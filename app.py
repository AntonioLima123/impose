import streamlit as st
import pypdf
import io
from pypdf import PageObject, Transformation

# Configuração da página
st.set_page_config(page_title="Imposição Industrial 32x45", page_icon="📖", layout="wide")

st.title("📖 Sistema de Imposição Profissional SRA3 (32x45)")
st.write("Imposição corrigida para revistas A5: as páginas são rodadas 90° para caberem na folha e alinhadas 'cabeça-com-cabeça'.")

# Dimensões SRA3 em pontos (1mm = 2.83465pt)
LARGURA_SRA3 = int(450 * 2.83465) # 1275 pt
ALTURA_SRA3 = int(320 * 2.83465)  # 907 pt

def colar_na_folha_pro(folha_destino, pag_orig, q_idx):
    """
    Posiciona a página num dos 4 quadrantes da folha 32x45.
    q_idx: 0=Inf.Esq, 1=Inf.Dir, 2=Sup.Esq, 3=Sup.Dir
    """
    larg_orig = float(pag_orig.mediabox.width)
    alt_orig = float(pag_orig.mediabox.height)
    
    # Dimensões do quadrante (Meia folha SRA3)
    q_larg = LARGURA_SRA3 / 2
    q_alt = ALTURA_SRA3 / 2
    
    # Coordenadas base do quadrante
    ox = (q_idx % 2) * q_larg
    oy = (1 if q_idx >= 2 else 0) * q_alt

    # --- LÓGICA DE ROTAÇÃO PARA ENCAIXE ---
    # Para A5 caber em SRA3, rodamos 90° base. 
    # Quadrantes inferiores (0,1): Cabeça para CIMA (+90°)
    # Quadrantes superiores (2,3): Cabeça para BAIXO (-90°) -> Cabeça-com-Cabeça
    
    rotacao = 90 if q_idx < 2 else -90
    
    # Escala: Após rodar 90°, a nova largura é a antiga altura
    escala = min(q_larg / alt_orig, q_alt / larg_orig) * 0.94
    
    # Centralização no quadrante
    w_final = alt_orig * escala
    h_final = larg_orig * escala
    mx = (q_larg - w_final) / 2
    my = (q_alt - h_final) / 2

    # Matriz de transformação
    transf = Transformation().scale(escala).rotate(rotacao)
    
    if rotacao == 90:
        transf = transf.translate(ox + mx + w_final, oy + my)
    else:
        transf = transf.translate(ox + mx, oy + my + h_final)

    # Aplicação segura
    temp_page = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
    temp_page.merge_page(pag_orig)
    temp_page.add_transformation(transf)
    folha_destino.merge_page(temp_page)

def desenhar_marcas_limpas(dobra_cruzada=False):
    overlay = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
    comandos = ["0.5 w", "0 0 0 RG", "[3 3] 0 d"] # Tracejado
    cx, cy = LARGURA_SRA3 / 2, ALTURA_SRA3 / 2
    m = 30 # tamanho da marca
    
    # Marcas de Dobra (apenas nas bordas)
    comandos.extend([f"{cx} 0 m {cx} {m} l S", f"{cx} {ALTURA_SRA3} m {cx} {ALTURA_SRA3-m} l S"])
    if dobra_cruzada:
        comandos.extend([f"0 {cy} m {m} {cy} l S", f"{LARGURA_SRA3} {cy} m {LARGURA_SRA3-m} {cy} l S"])
    
    overlay._contents = "\n".join(comandos).encode()
    return overlay

# --- INTERFACE ---
uploaded_file = st.file_uploader("Upload PDF Original", type=["pdf"])

if uploaded_file:
    reader = pypdf.PdfReader(uploaded_file)
    pags = list(reader.pages)
    
    # Garantir múltiplo de 8 para A5
    while len(pags) % 8 != 0:
        pags.append(PageObject.create_blank_page(width=pags[0].mediabox.width, height=pags[0].mediabox.height))
    
    total = len(pags)
    st.success(f"PDF pronto: {total} páginas.")

    # Preview Visual da Imposição
    st.subheader("🗺️ Mapa de Imposição (Folha 1)")
    col1, col2 = st.columns(2)
    with col1:
        st.info("**FRENTE**\n\n[ Pág 5 ⬇️ ] [ Pág 4 ⬇️ ]\n\n[ Pág 8 ⬆️ ] [ Pág 1 ⬆️ ]")
    with col2:
        st.info("**VERSO**\n\n[ Pág 3 ⬇️ ] [ Pág 6 ⬇️ ]\n\n[ Pág 2 ⬆️ ] [ Pág 7 ⬆️ ]")

    if st.button("Gerar PDF Industrial 🚀"):
        writer = pypdf.PdfWriter()
        marcas = desenhar_marcas_limpas(dobra_cruzada=True)

        for i in range(0, total, 8):
            b = pags[i:i+8]
            
            # FRENTE
            frente = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
            colar_na_folha_pro(frente, b[4], 2) # P5 Sup Esq
            colar_na_folha_pro(frente, b[3], 3) # P4 Sup Dir
            colar_na_folha_pro(frente, b[7], 0) # P8 Inf Esq
            colar_na_folha_pro(frente, b[0], 1) # P1 Inf Dir
            frente.merge_page(marcas)
            writer.add_page(frente)
            
            # VERSO
            verso = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
            colar_na_folha_pro(verso, b[2], 2) # P3 Sup Esq
            colar_na_folha_pro(verso, b[5], 3) # P6 Sup Dir
            colar_na_folha_pro(verso, b[1], 0) # P2 Inf Esq
            colar_na_folha_pro(verso, b[6], 1) # P7 Inf Dir
            verso.merge_page(marcas)
            writer.add_page(verso)

        output = io.BytesIO()
        writer.write(output)
        st.download_button("Baixar PDF 32x45 Corrigido", output.getvalue(), "imposicao_A5_SRA3.pdf")
