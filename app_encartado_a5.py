import streamlit as st
import pypdf
import io
from pypdf import PageObject, Transformation
from reportlab.pdfgen import canvas

# Configuração da página da plataforma
st.set_page_config(page_title="Imposição A5 Encartado 32x45", page_icon="📖", layout="wide")

st.title("📖 Sistema de Imposição Gráfica - Alceamento / Encartado A5")
st.write("Gere esquemas de imposição reais baseados no boneco físico de dobra cruzada para formato **Vertical A5 (Folha SRA3 320mm x 450mm)**.")

# DIMENSÕES EXATAS DA FOLHA VERTICAL 32x45 EM PONTOS (1 mm = 2.83465 pontos)
MM_TO_PTS = 2.83465
LARGURA_SRA3 = int(320 * MM_TO_PTS)  # 907 pt (Eixo X)
ALTURA_SRA3 = int(450 * MM_TO_PTS)   # 1275 pt (Eixo Y)

# Eixos centrais da folha SRA3 (Linhas de dobra/corte centrais)
CX = LARGURA_SRA3 / 2
CY = ALTURA_SRA3 / 2

# FORMATO DE CORTE ALVO PARA CADA PÁGINA A5
LARGURA_A5_ALVO = 148.5 * MM_TO_PTS  # 148.5 mm
ALTURA_A5_ALVO = 210.0 * MM_TO_PTS   # 210.0 mm

# --- SIDEBAR DE CONTROLO INDUSTRIAL ---
st.sidebar.header("⚙️ Ajustes de Precisão Gráfica")
compensacao_dobra_mm = st.sidebar.slider("Compensação na Dobra Vertical (mm)", min_value=0.0, max_value=5.0, value=1.0, step=0.5)
compensacao_corte_mm = st.sidebar.slider("Compensação no Corte Horizontal (mm)", min_value=0.0, max_value=10.0, value=2.0, step=0.5)

incluir_corte = st.sidebar.checkbox("Incluir Marcas de Corte", value=True)
incluir_dobra = st.sidebar.checkbox("Incluir Marcas de Dobra", value=True)

# Conversão dos milímetros escolhidos para pontos (Pt)
COMPENSACAO_VERT = compensacao_dobra_mm * MM_TO_PTS
COMPENSACAO_HORIZ = compensacao_corte_mm * MM_TO_PTS

def gerar_marcas_reais(largura_folha, altura_folha, marcas_corte, marcas_dobra):
    """Desenha as marcas de corte e dobra perfeitamente deslocadas pelas compensações dos eixos"""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(largura_folha, altura_folha))
    
    can.setStrokeColorRGB(0, 0, 0)
    can.setLineWidth(0.4)
    
    comprimento_marca = 15
    
    # As marcas acompanham exatamente o deslocamento real que damos às páginas
    afastamento_x = CX - LARGURA_A5_ALVO - COMPENSACAO_VERT
    afastamento_y = CY - ALTURA_A5_ALVO - COMPENSACAO_HORIZ
    
    if marcas_dobra:
        can.setDash(2, 2)
        # Dobra Vertical Central
        can.line(CX, altura_folha, CX, altura_folha - comprimento_marca)
        can.line(CX, 0, CX, comprimento_marca)
        # Dobra Horizontal Central
        can.line(0, CY, comprimento_marca, CY)
        can.line(largura_folha, CY, largura_folha - comprimento_marca, CY)
            
    if marcas_corte:
        can.setDash()
        # Marcas verticais (Limites laterais de corte do A5)
        can.line(afastamento_x, altura_folha, afastamento_x, altura_folha - comprimento_marca)
        can.line(largura_folha - afastamento_x, altura_folha, largura_folha - afastamento_x, altura_folha - comprimento_marca)
        can.line(afastamento_x, 0, afastamento_x, comprimento_marca)
        can.line(largura_folha - afastamento_x, 0, largura_folha - afastamento_x, comprimento_marca)
        
        # Marcas horizontais (Limites superior/inferior de corte do A5)
        can.line(0, afastamento_y, comprimento_marca, afastamento_y)
        can.line(0, altura_folha - afastamento_y, comprimento_marca, altura_folha - afastamento_y)
        can.line(largura_folha, afastamento_y, largura_folha - comprimento_marca, afastamento_y)
        can.line(largura_folha, altura_folha - afastamento_y, largura_folha - comprimento_marca, altura_folha - afastamento_y)
        
    can.save()
    packet.seek(0)
    return pypdf.PdfReader(packet).pages[0]

def colar_com_ajuste_duplo(folha_destino, pag_orig, lado_esquerdo=True, no_topo=True, rodar_180=False):
    """Posiciona a página aplicando de forma independente os afastamentos de X (dobra) e Y (guilhotina)"""
    try:
        larg_orig = float(pag_orig.mediabox.width)
        alt_orig = float(pag_orig.mediabox.height)
    except Exception:
        larg_orig, alt_orig = 420.0, 595.0

    # Força a escala real ao tamanho milimétrico do A5 industrial (evita reduções fantasmas)
    escala = min(LARGURA_A5_ALVO / larg_orig, ALTURA_A5_ALVO / alt_orig)
    w_f = larg_orig * escala
    h_f = alt_orig * escala
    
    # 1. POSICIONAMENTO NO EIXO X (Dobra Vertical / Lombada)
    if lado_esquerdo:
        ox = CX - w_f - COMPENSACAO_VERT
    else:
        ox = CX + COMPENSACAO_VERT
        
    # 2. POSICIONAMENTO NO EIXO Y (Corte/Guilhotina Horizontal)
    if no_topo:
        # Linha de cima: afasta para cima a partir do centro (Cabeça com cabeça)
        oy = CY + COMPENSACAO_HORIZ
    else:
        # Linha de baixo: afasta para baixo a partir do centro
        oy = CY - h_f - COMPENSACAO_HORIZ

    transf = Transformation().scale(escala)
    
    if rodar_180:
        transf = transf.rotate(180).translate(ox + w_f, oy + h_f)
    else:
        transf = transf.translate(ox, oy)
            
    pag_temp = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
    pag_temp.merge_page(pag_orig)
    pag_temp.add_transformation(transf)
    folha_destino.merge_page(pag_temp)

# --- FLUXO PRINCIPAL (INTERFACE DO UTILIZADOR) ---
uploaded_file = st.file_uploader("Selecione o ficheiro PDF da Revista (Tamanho A5 idealmente)", type=["pdf"])

if uploaded_file is not None:
    reader = pypdf.PdfReader(uploaded_file)
    paginas = list(reader.pages)
    total_orig = len(paginas)
    
    st.info(f"Ficheiro lido com sucesso! Total de páginas original: **{total_orig}**")
    
    # Preservado o teu ajuste automático global para múltiplos de 8 (Exigência para fechar a grelha de encarte 2x2)
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

    if st.button("Gerar Imposição Final A5 Encartado 🚀"):
        try:
            writer = pypdf.PdfWriter()
            marcas_f = gerar_marcas_reais(LARGURA_SRA3, ALTURA_SRA3, incluir_corte, incluir_dobra)
            
            # Cada folha física SRA3 processa 8 páginas (4 frente, 4 verso)
            total_folhas = total_orig // 8
            
            for f in range(total_folhas):
                # ALGORITMO INTEGRADO DO BONECO REAL DO UTILIZADOR (Índices base 0)
                n = total_orig
                
                # --- MAPA DA FRENTE (FACE A) ---
                frente_sup_esq = 4 * f
                frente_sup_dir = n - 1 - (4 * f)
                frente_inf_esq = 3 + (4 * f)
                frente_inf_dir = n - 4 - (4 * f)
                
                # --- MAPA DO VERSO (FACE B) ---
                verso_sup_esq = n - 2 - (4 * f)
                verso_sup_dir = 1 + (4 * f)
                verso_inf_esq = n - 3 - (4 * f)
                verso_inf_dir = 2 + (4 * f)
                
                # --- EXECUTAR MONTAGEM DA FRENTE ---
                folha_frente = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                # Linha Superior (Invertidas 180° - no topo)
                colar_com_ajuste_duplo(folha_frente, paginas[frente_sup_esq], lado_esquerdo=True, no_topo=True, rodar_180=True)
                colar_com_ajuste_duplo(folha_frente, paginas[frente_sup_dir], lado_esquerdo=False, no_topo=True, rodar_180=True)
                # Linha Inferior (Direitas 0° - na base)
                colar_com_ajuste_duplo(folha_frente, paginas[frente_inf_esq], lado_esquerdo=True, no_topo=False, rodar_180=False)
                colar_com_ajuste_duplo(folha_frente, paginas[frente_inf_dir], lado_esquerdo=False, no_topo=False, rodar_180=False)
                
                folha_frente.merge_page(marcas_f)
                writer.add_page(folha_frente)
                
                # --- EXECUTAR MONTAGEM DO VERSO ---
                folha_verso = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                # Linha Superior (Invertidas 180° - no topo)
                colar_com_ajuste_duplo(folha_verso, paginas[verso_sup_esq], lado_esquerdo=True, no_topo=True, rodar_180=True)
                colar_com_ajuste_duplo(folha_verso, paginas[verso_sup_dir], lado_esquerdo=False, no_topo=True, rodar_180=True)
                # Linha Inferior (Direitas 0° - na base)
                colar_com_ajuste_duplo(folha_verso, paginas[verso_inf_esq], lado_esquerdo=True, no_topo=False, rodar_180=False)
                colar_com_ajuste_duplo(folha_verso, paginas[verso_inf_dir], lado_esquerdo=False, no_topo=False, rodar_180=False)
                
                folha_verso.merge_page(marcas_f)
                writer.add_page(folha_verso)
                
            output_pdf = io.BytesIO()
            writer.write(output_pdf)
            output_pdf.seek(0)
            
            st.success("🎉 Imposição Alceada A5 gerada e calibrada com o seu boneco físico!")
            st.download_button(
                label="Descarregar Ficheiro Imposição Encartado A5 📥",
                data=output_pdf,
                file_name="imposicao_A5_encartado_saddle.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"❌ Erro no processamento: {str(e)}")
