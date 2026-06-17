import streamlit as st
import pypdf
import io
from pypdf import PageObject, Transformation
from reportlab.pdfgen import canvas

# Configuração da página da plataforma
st.set_page_config(page_title="Imposição A5 Encartado 32x45", page_icon="📖", layout="wide")

st.title("📖 Sistema de Imposição Gráfica - Alceamento / Encartado A5")
st.write("Gere esquemas de imposição reais para revistas agrafadas ao centro (**Saddle Stitch**) em formato **Vertical A5 (Folha SRA3 320mm x 450mm)**.")

# DIMENSÕES EXATAS DA FOLHA VERTICAL 32x45 EM PONTOS (1 mm = 2.83465 pontos)
LARGURA_SRA3 = int(320 * 2.83465)  # 907 pt (Eixo X)
ALTURA_SRA3 = int(450 * 2.83465)   # 1275 pt (Eixo Y)

def gerar_marcas_reportlab(largura_folha, altura_folha, marcas_corte=True, marcas_dobra=True):
    """Gere as marcas de corte e dobra cruzada estritamente por FORA da área útil do impresso"""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(largura_folha, altura_folha))
    
    can.setStrokeColorRGB(0, 0, 0)
    can.setLineWidth(0.5)
    
    cx = largura_folha / 2
    cy = altura_folha / 2
    comprimento_marca = 20
    afastamento = 15  # Margem para as guias não invadirem o impresso útil
    
    if marcas_dobra:
        can.setDash(3, 3)
        # Linha de Dobra Vertical Central
        can.line(cx, altura_folha, cx, altura_folha - comprimento_marca)
        can.line(cx, 0, cx, comprimento_marca)
        # Linha de Dobra Horizontal Central (Obrigatória para Grelha 2x2 do A5)
        can.line(0, cy, comprimento_marca, cy)
        can.line(largura_folha, cy, largura_folha - comprimento_marca, cy)
            
    if marcas_corte:
        can.setDash()
        # Canto Superior Esquerdo
        can.line(afastamento, altura_folha, afastamento, altura_folha - comprimento_marca)
        can.line(0, altura_folha - afastamento, comprimento_marca, altura_folha - afastamento)
        
        # Canto Superior Direito
        can.line(largura_folha - afastamento, altura_folha, largura_folha - afastamento, altura_folha - comprimento_marca)
        can.line(largura_folha, altura_folha - afastamento, largura_folha - comprimento_marca, altura_folha - afastamento)
        
        # Canto Inferior Esquerdo
        can.line(afastamento, 0, afastamento, comprimento_marca)
        can.line(0, afastamento, comprimento_marca, afastamento)
        
        # Canto Inferior Direito
        can.line(largura_folha - afastamento, 0, largura_folha - afastamento, comprimento_marca)
        can.line(largura_folha, afastamento, largura_folha - comprimento_marca, afastamento)
        
    can.save()
    packet.seek(0)
    marcas_reader = pypdf.PdfReader(packet)
    return marcas_reader.pages[0]

def colar_na_folha_industrial(folha_destino, pag_orig, q_larg, alt_quad, ox, oy, rodar_180=False):
    """Insere a página mantendo a orientação vertical (em pé) nativa e aplicando 180° onde necessário"""
    try:
        larg_orig = float(pag_orig.mediabox.width)
        alt_orig = float(pag_orig.mediabox.height)
    except Exception:
        larg_orig, alt_orig = 420.0, 595.0
        
    if larg_orig <= 0 or alt_orig <= 0:
        larg_orig, alt_orig = 420.0, 595.0

    # Escala mantendo as proporções verticais dentro do quadrante vertical dedicado
    escala = min(q_larg / larg_orig, alt_quad / alt_orig) * 0.92
    w_f = larg_orig * escala
    h_f = alt_orig * escala
        
    mx = (q_larg - w_f) / 2
    my = (alt_quad - h_f) / 2
    
    transf = Transformation().scale(escala)
    
    if rodar_180:
        # Cabeça com cabeça: roda 180 graus para inverter a orientação vertical
        transf = transf.rotate(180).translate(ox + mx + w_f, oy + my + h_f)
    else:
        # Posição em pé normal (0 graus)
        transf = transf.translate(ox + mx, oy + my)
            
    pag_temp = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
    pag_temp.merge_page(pag_orig)
    pag_temp.add_transformation(transf)
    folha_destino.merge_page(pag_temp)

# --- INTERFACE ---
st.sidebar.header("⚙️ Configurações das Marcas")
incluir_corte = st.sidebar.checkbox("Incluir Marcas de Corte", value=True)
incluir_dobra = st.sidebar.checkbox("Incluir Marcas de Dobra", value=True)

uploaded_file = st.file_uploader("Selecione o ficheiro PDF da Revista (Tamanho A5 idealmente)", type=["pdf"])

if uploaded_file is not None:
    reader = pypdf.PdfReader(uploaded_file)
    paginas = list(reader.pages)
    total_orig = len(paginas)
    
    st.info(f"Ficheiro lido com sucesso! Total de páginas original: **{total_orig}**")
    
    # Ajuste automático global para múltiplos de 8 (Exigência para fechar a grelha de encarte 2x2)
    resto = total_orig % 8
    if resto != 0:
        pag_em_falta = 8 - resto
        st.warning(f"⚠️ Ajuste do Livro: Adicionadas {pag_em_falta} páginas em branco para fechar o ciclo de encarte.")
        try:
            larg_p = float(paginas[0].mediabox.width)
            alt_p = float(paginas[0].mediabox.height)
        except Exception:
            larg_p, alt_p = 420.0, 595.0
        for _ in range(pag_em_falta):
            paginas.append(PageObject.create_blank_page(width=larg_p, height=alt_p))
        total_orig = len(paginas)

    if st.button("Gerar Imposição Final A5 Alceado 🚀"):
        try:
            writer = pypdf.PdfWriter()
            
            # GRELHA FIXA A5 (2 COLUNAS X 2 LINHAS)
            larg_quad = LARGURA_SRA3 / 2
            alt_quad = ALTURA_SRA3 / 2
            
            marcas_f = gerar_marcas_reportlab(LARGURA_SRA3, ALTURA_SRA3, incluir_corte, incluir_dobra)
            
            # Cada folha SRA3 processa 8 páginas (4 na frente, 4 no verso)
            total_folhas = total_orig // 8
            
            for f in range(total_folhas):
                # --- MAPEAMENTO MATEMÁTICO REAL PARA DOBRA CRUZADA ENCARTADA ---
                # n = total_orig (ex: 16). f = índice da folha (0 para a primeira folha externa)
                n = total_orig
                
                # Páginas da FRENTE (Face A)
                # Ex para f=0 e n=16: sup_esq = 16, sup_dir = 1, inf_esq = 13, inf_dir = 4
                frente_sup_esq = n - 1 - (2 * f)
                frente_sup_dir = 2 * f
                frente_inf_esq = n - 4 - (2 * f)
                frente_inf_dir = 3 + (2 * f)
                
                # Páginas do VERSO (Face B) - Espelho exato para bater correto frente/verso
                # Ex para f=0 e n=16: sup_esq = 2, sup_dir = 15, inf_esq = 5, inf_dir = 12
                verso_sup_esq = 1 + (2 * f)
                verso_sup_dir = n - 2 - (2 * f)
                verso_inf_esq = 4 + (2 * f)
                verso_inf_dir = n - 5 - (2 * f)
                
                # --- PROCESSAR FRENTE ---
                folha_frente = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                
                # Linha Superior (Cabeça com cabeça -> Rotação 180°)
                colar_na_folha_industrial(folha_frente, paginas[frente_sup_esq], larg_quad, alt_quad, 0, alt_quad, rodar_180=True)
                colar_na_folha_industrial(folha_frente, paginas[frente_sup_dir], larg_quad, alt_quad, larg_quad, alt_quad, rodar_180=True)
                
                # Linha Inferior (Páginas em pé -> Rotação 0°)
                colar_na_folha_industrial(folha_frente, paginas[frente_inf_esq], larg_quad, alt_quad, 0, 0, rodar_180=False)
                colar_na_folha_industrial(folha_frente, paginas[frente_inf_dir], larg_quad, alt_quad, larg_quad, 0, rodar_180=False)
                
                folha_frente.merge_page(marcas_f)
                writer.add_page(folha_frente)
                
                # --- PROCESSAR VERSO ---
                folha_verso = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                
                # Linha Superior (Cabeça com cabeça -> Rotação 180°)
                colar_na_folha_industrial(folha_verso, paginas[verso_sup_esq], larg_quad, alt_quad, 0, alt_quad, rodar_180=True)
                colar_na_folha_industrial(folha_verso, paginas[verso_sup_dir], larg_quad, alt_quad, larg_quad, alt_quad, rodar_180=True)
                
                # Linha Inferior (Páginas em pé -> Rotação 0°)
                colar_na_folha_industrial(folha_verso, paginas[verso_inf_esq], larg_quad, alt_quad, 0, 0, rodar_180=False)
                colar_na_folha_industrial(folha_verso, paginas[verso_inf_dir], larg_quad, alt_quad, larg_quad, 0, rodar_180=False)
                
                folha_verso.merge_page(marcas_f)
                writer.add_page(folha_verso)
                
            output_pdf = io.BytesIO()
            writer.write(output_pdf)
            output_pdf.seek(0)
            
            st.success("🎉 Imposição de Revista Encartada (Saddle Stitch) A5 corrigida com sucesso!")
            st.download_button(
                label="Descarregar Ficheiro Imposição Encartado A5 📥",
                data=output_pdf,
                file_name="imposicao_A5_encartado_saddle.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"❌ Erro no processamento: {str(e)}")
