import streamlit as st
import pypdf
import io
from pypdf import PageObject, Transformation
from reportlab.pdfgen import canvas

# Configuração da página da plataforma
st.set_page_config(page_title="Imposição Profissional 32x45", page_icon="📖", layout="wide")

st.title("📖 Sistema de Imposição Gráfica Profissional (Formato Vertical 32x45)")
st.write("Gere esquemas de imposição reais para gráfica em formato **Vertical (320mm x 450mm)** com marcas periféricas externas.")

# DIMENSÕES EXATAS DA FOLHA VERTICAL 32x45 EM PONTOS (1 mm = 2.83465 pontos)
LARGURA_SRA3 = int(320 * 2.83465)  # 907 pt (Eixo X)
ALTURA_SRA3 = int(450 * 2.83465)   # 1275 pt (Eixo Y)

def gerar_marcas_reportlab(largura_folha, altura_folha, marcas_corte=True, marcas_dobra=True, dobra_cruzada=False):
    """Gere as marcas de corte e dobra estritamente por FORA da área útil do impresso"""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(largura_folha, altura_folha))
    
    can.setStrokeColorRGB(0, 0, 0)
    can.setLineWidth(0.5)
    
    cx = largura_folha / 2
    cy = altura_folha / 2
    comprimento_marca = 20
    afastamento = 15 # Margem para as guias não invadirem o impresso útil
    
    if marcas_dobra:
        can.setDash(3, 3)
        # Linha de Dobra Vertical Central
        can.line(cx, altura_folha, cx, altura_folha - comprimento_marca)
        can.line(cx, 0, cx, comprimento_marca)
        if dobra_cruzada:
            # Linha de Dobra Horizontal Central
            can.line(0, cy, comprimento_marca, cy)
            can.line(largura_folha, cy, largura_folha - comprimento_marca, cy)
            
    if marcas_corte:
        can.setDash()
        # Cantos Exteriores recuados (Bleed/Afastamento de segurança)
        # Canto Superior Esquerdo
        can.line(afastamento, altura_folha, afastamento, altura_folha - comprimento_marca)
        can.line(0, altura_folha - afastamento, comprimento_marca, altura_folha - afastamento)
        # Canto Superior Direito
        can.line(largura_folha - afastamento, altura_folha, largura_folha - afastamento, altura_folha - comprimento_marca)
        can.line(largura_folha, altura_folha - afastamento, largura_fox = largura_folha - comprimento_marca, y = altura_folha - afastamento)
        # Ajuste de linha contínua do canto superior direito
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
st.sidebar.header("⚙️ Definições de Imposição")
modo = st.sidebar.selectbox("Formato Final da Revista", [
    "Revista A4 (Caderno de 4 Páginas - Dobra Única)", 
    "Revista A5 (Caderno de 8 Páginas - Dobra Cruzada Mecânica)"
])
incluir_corte = st.sidebar.checkbox("Incluir Marcas de Corte (Exteriores)", value=True)
incluir_dobra = st.sidebar.checkbox("Incluir Marcas de Dobra (Sangria)", value=True)

uploaded_file = st.file_uploader("Selecione o ficheiro PDF da Revista", type=["pdf"])

if uploaded_file is not None:
    reader = pypdf.PdfReader(uploaded_file)
    paginas = list(reader.pages)
    total_orig = len(paginas)
    
    st.info(f"Ficheiro lido com sucesso! Total de páginas: **{total_orig}**")
    
    multiplo = 4 if "A4" in modo else 8
    resto = total_orig % multiplo
    if resto != 0:
        pag_em_falta = multiplo - resto
        st.warning(f"⚠️ Ajuste de Caderno: Adicionadas {pag_em_falta} páginas em branco.")
        try:
            larg_p = float(paginas[0].mediabox.width)
            alt_p = float(paginas[0].mediabox.height)
        except Exception:
            larg_p, alt_p = 420.0, 595.0
