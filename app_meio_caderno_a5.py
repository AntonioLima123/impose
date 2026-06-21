import streamlit as st
import pypdf
import io
from pypdf import PageObject, Transformation
from reportlab.pdfgen import canvas

# Configuração da página da plataforma
st.set_page_config(page_title="Imposição A5 Meio Caderno 32x45", page_icon="✂️", layout="wide")

st.title("✂️ Sistema de Imposição Gráfica - Meio Caderno A5 (Tira/Retira)")
st.write("Gere o esquema de imposição para **1/2 Caderno (4 páginas)** no formato **Vertical A5 (Folha SRA3 320mm x 450mm)** em modo Tira/Retira.")

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
    afastamento = 15
    
    if marcas_dobra:
        can.setDash(3, 3)
        # Linha de Dobra Vertical Central
        can.line(cx, altura_folha, cx, altura_folha - comprimento_marca)
        can.line(cx, 0, cx, comprimento_marca)
        # Linha de Dobra Horizontal Central
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
    """Insere a página mantendo a orientação vertical nativa e aplicando 180° onde necessário"""
    try:
        larg_orig = float(pag_orig.mediabox.width)
        alt_orig = float(pag_orig.mediabox.height)
    except Exception:
        larg_orig, alt_orig = 420.0, 595.0
        
    if larg_orig <= 0 or alt_orig <= 0:
        larg_orig, alt_orig = 420.0, 595.0

    escala = min(q_larg / larg_orig, alt_quad / alt_orig) * 0.92
    w_f = larg_orig * escala
    h_f = alt_orig * escala
        
    mx = (q_larg - w_f) / 2
    my = (alt_quad - h_f) / 2
    
    transf = Transformation().scale(escala)
    
    if rodar_180:
        transf = transf.rotate(180).translate(ox + mx + w_f, oy + my + h_f)
    else:
        transf = transf.translate(ox + mx, oy + my)
            
    pag_temp = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
    pag_temp.merge_page(pag_orig)
    pag_temp.add_transformation(transf)
    folha_destino.merge_page(pag_temp)

# --- INTERFACE ---
st.sidebar.header("⚙️ Configurações das Marcas")
incluir_corte = st.sidebar.checkbox("Incluir Marcas de Corte", value=True)
incluir_dobra = st.sidebar.checkbox("Incluir Marcas de Dobra", value=True)

uploaded_file = st.file_uploader("Selecione o PDF de 4 Páginas (Meio Caderno)", type=["pdf"])

if uploaded_file is not None:
    reader = pypdf.PdfReader(uploaded_file)
    paginas = list(reader.pages)
    total_orig = len(paginas)
    
    if total_orig != 4:
        st.error(f"❌ Erro: O ficheiro selecionado contém {total_orig} páginas. Este módulo aceita estritamente ficheiros com 4 páginas.")
    else:
        st.success("Ficheiro de 4 páginas validado com sucesso!")
        
        if st.button("Gerar Imposição Meio Caderno A5 🚀"):
            try:
                writer = pypdf.PdfWriter()
                
                # GRELHA FIXA 2 COLUNAS X 2 LINHAS
                larg_quad = LARGURA_SRA3 / 2
                alt_quad = ALTURA_SRA3 / 2
                
                marcas_f = gerar_marcas_reportlab(LARGURA_SRA3, ALTURA_SRA3, incluir_corte, incluir_dobra)
                
                # --- MONTAGEM DA FOLHA TIRA/RETIRA ---
                # Mapeamento estrito com base na regra do operador:
                # P1 = Índice 0 | P2 = Índice 1 | P3 (Penúltima) = Índice 2 | P4 (Última) = Índice 3
                folha_unica = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                
                # Linha Superior (Invertidas 180° - Cabeça com cabeça)
                # Topo Esquerdo: Penúltima (P3)
                colar_na_folha_industrial(folha_unica, paginas[2], larg_quad, alt_quad, 0, alt_quad, rodar_180=True)
                # Topo Direito: Página 2
                colar_na_folha_industrial(folha_unica, paginas[1], larg_quad, alt_quad, larg_quad, alt_quad, rodar_180=True)
                
                # Linha Inferior (Direitas 0°)
                # Base Esquerda: Última (P4)
                colar_na_folha_industrial(folha_unica, paginas[3], larg_quad, alt_quad, 0, 0, rodar_180=False)
                # Base Direita: Página 1
                colar_na_folha_industrial(folha_unica, paginas[0], larg_quad, alt_quad, larg_quad, 0, rodar_180=False)
                
                # Aplica as marcas industriais
                folha_unica.merge_page(marcas_f)
                
                # Sendo Tira/Retira digital, adicionamos a mesma folha como Frente e Verso 
                # para que o RIP da máquina imprima os dois lados iguais automaticamente.
                writer.add_page(folha_unica)
                writer.add_page(folha_unica)
                
                output_pdf = io.BytesIO()
                writer.write(output_pdf)
                output_pdf.seek(0)
                
                st.success("🎉 Imposição de Meio Caderno A5 gerada!")
                st.download_button(
                    label="Descarregar Meio Caderno A5 Tira/Retira 📥",
                    data=output_pdf,
                    file_name="imposicao_meio_caderno_A5.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"❌ Erro no processamento: {str(e)}")
