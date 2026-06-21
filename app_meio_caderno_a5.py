import streamlit as st
import pypdf
import io
from pypdf import PageObject, Transformation
from reportlab.pdfgen import canvas

# Configuração da página da plataforma
st.set_page_config(page_title="Imposição A5 Meio Caderno Calibrado", page_icon="✂️", layout="wide")

st.title("✂️ Sistema de Imposição Gráfica - Meio Caderno A5 (Precisão Digital)")
st.write("Gere a imposição para **1/2 Caderno (4 páginas)** em SRA3 Vertical com controlo micrométrico de medianiz e escala real.")

# DIMENSÕES EXATAS DA FOLHA VERTICAL 32x45 EM PONTOS (1 mm = 2.83465 pontos)
MM_TO_PTS = 2.83465
LARGURA_SRA3 = int(320 * MM_TO_PTS)  # 907 pt
ALTURA_SRA3 = int(450 * MM_TO_PTS)   # 1275 pt

# Eixos centrais da folha SRA3 (Linhas de dobra)
CX = LARGURA_SRA3 / 2
CY = ALTURA_SRA3 / 2

# PARÂMETROS GRÁFICOS DE PRECISÃO
LARGURA_A5_ALVO = 148.5 * MM_TO_PTS  # Formato final de corte (Metade da largura útil teórica)
ALTURA_A5_ALVO = 210.0 * MM_TO_PTS   # Formato final de corte (Metade da altura útil teórica)

st.sidebar.header("⚙️ Ajustes de Precisão Gráfica")
compensacao_dobra_mm = st.sidebar.slider("Compensação na Dobra Vertical (mm)", min_value=0.0, max_value=3.0, value=1.0, step=0.5)
incluir_corte = st.sidebar.checkbox("Incluir Marcas de Corte", value=True)
incluir_dobra = st.sidebar.checkbox("Incluir Marcas de Dobra", value=True)

COMPENSACAO_DOBRA = compensacao_dobra_mm * MM_TO_PTS

def gerar_marcas_reais(largura_folha, altura_folha, marcas_corte, marcas_dobra):
    """Desenha as marcas de corte alinhadas milimetricamente com o tamanho real do A5 imposto"""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(largura_folha, altura_folha))
    
    can.setStrokeColorRGB(0, 0, 0)
    can.setLineWidth(0.4)
    
    comprimento_marca = 15
    # O recuo baseia-se no tamanho real que o bloco A5 ocupa a partir do centro
    afastamento_x = CX - LARGURA_A5_ALVO
    afastamento_y = CY - ALTURA_A5_ALVO
    
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
        # Marcas verticais externas (limites laterais do corte A5)
        can.line(afastamento_x, altura_folha, afastamento_x, altura_folha - comprimento_marca)
        can.line(largura_folha - afastamento_x, altura_folha, largura_folha - afastamento_x, altura_folha - comprimento_marca)
        can.line(afastamento_x, 0, afastamento_x, comprimento_marca)
        can.line(largura_folha - afastamento_x, 0, largura_folha - afastamento_x, comprimento_marca)
        
        # Marcas horizontais externas (limites superior/inferior do corte A5)
        can.line(0, afastamento_y, comprimento_marca, afastamento_y)
        can.line(0, altura_folha - afastamento_y, comprimento_marca, altura_folha - afastamento_y)
        can.line(largura_folha, afastamento_y, largura_folha - comprimento_marca, afastamento_y)
        can.line(largura_folha, altura_folha - afastamento_y, largura_folha - comprimento_marca, altura_folha - afastamento_y)
        
    can.save()
    packet.seek(0)
    return pypdf.PdfReader(packet).pages[0]

def colar_com_ancoragem_central(folha_destino, pag_orig, lado_esquerdo=True, no_topo=True, rodar_180=False):
    """Cola a página colada ao eixo central (lombada), aplicando apenas a folga de dobra necessária"""
    try:
        larg_orig = float(pag_orig.mediabox.width)
        alt_orig = float(pag_orig.mediabox.height)
    except Exception:
        larg_orig, alt_orig = 420.0, 595.0

    # Escala estrita para o tamanho real do fólio A5 industrial (sem reduções arbitrárias)
    escala = min(LARGURA_A5_ALVO / larg_orig, ALTURA_A5_ALVO / alt_orig)
    w_f = larg_orig * escala
    h_f = alt_orig * escala
    
    # 1. CÁLCULO DO EIXO X (Ancorado à dobra vertical central)
    if lado_esquerdo:
        # Colado à esquerda do centro, recuando a compensação de dobra
        ox = CX - w_f - COMPENSACAO_DOBRA
    else:
        # Colado à direita do centro, avançando a compensação de dobra
        ox = CX + COMPENSACAO_DOBRA
        
    # 2. CÁLCULO DO EIXO Y (Alinhamento horizontal na folha)
    if no_topo:
        # Na linha de cima, encostado à dobra horizontal central para o "cabeça com cabeça"
        oy = CY
    else:
        # Na linha de baixo, encostado à dobra horizontal central
        oy = CY - h_f

    transf = Transformation().scale(escala)
    
    if rodar_180:
        transf = transf.rotate(180).translate(ox + w_f, oy + h_f)
    else:
        transf = transf.translate(ox, oy)
            
    pag_temp = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
    pag_temp.merge_page(pag_orig)
    pag_temp.add_transformation(transf)
    folha_destino.merge_page(pag_temp)

# --- INTERFACE DE CARREGAMENTO ---
uploaded_file = st.file_uploader("Selecione o PDF de 4 Páginas (Meio Caderno)", type=["pdf"])

if uploaded_file is not None:
    reader = pypdf.PdfReader(uploaded_file)
    paginas = list(reader.pages)
    total_orig = len(paginas)
    
    if total_orig != 4:
        st.error(f"❌ Erro: O ficheiro contém {total_orig} páginas. Forneça um ficheiro com exatamente 4 páginas.")
    else:
        st.success("Ficheiro de 4 páginas validado!")
        
        if st.button("Gerar Imposição Calibrada 🚀"):
            try:
                writer = pypdf.PdfWriter()
                marcas_f = gerar_marcas_reais(LARGURA_SRA3, ALTURA_SRA3, incluir_corte, incluir_dobra)
                
                folha_unica = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                
                # --- MONTAGEM DA GRELHA COM ANCORAGEM CENTRAL ---
                # Topo Esquerdo: Penúltima (P3) -> Invertida
                colar_com_ancoragem_central(folha_unica, paginas[2], lado_esquerdo=True, no_topo=True, rodar_180=True)
                # Topo Direito: Página 2 -> Invertida
                colar_com_ancoragem_central(folha_unica, paginas[1], lado_esquerdo=False, no_topo=True, rodar_180=True)
                
                # Base Esquerda: Última (P4) -> Direita
                colar_com_ancoragem_central(folha_unica, paginas[3], lado_esquerdo=True, no_topo=False, rodar_180=False)
                # Base Direita: Página 1 -> Direita
                colar_com_ancoragem_central(folha_unica, paginas[0], lado_esquerdo=False, no_topo=False, rodar_180=False)
                
                # Mesclar marcas perfeitamente ajustadas ao bloco
                folha_unica.merge_page(marcas_f)
                
                # Adiciona duas páginas iguais para o fluxo Tira/Retira Digital
                writer.add_page(folha_unica)
                writer.add_page(folha_unica)
                
                output_pdf = io.BytesIO()
                writer.write(output_pdf)
                output_pdf.seek(0)
                
                st.success("🎉 Imposição micrométrica gerada com sucesso!")
                st.download_button(
                    label="Descarregar PDF de Alta Precisão 📥",
                    data=output_pdf,
                    file_name="imposicao_A5_meio_caderno_precisao.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"❌ Erro no processamento: {str(e)}")
