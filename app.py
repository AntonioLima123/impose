import streamlit as st
import pypdf
import io
from pypdf import PageObject, Transformation
from reportlab.pdfgen import canvas

# Configuração da página da plataforma
st.set_page_config(page_title="Imposição Profissional 32x45", page_icon="📖", layout="wide")

st.title("📖 Sistema de Imposição Gráfica Profissional (Formato 32x45)")
st.write("Gere esquemas de imposição reais para gráfica em formato **SRA3 (320mm x 450mm)** com marcas periféricas e rotações automáticas.")

# Dimensões do papel de saída SRA3 em pontos (1 mm = 2.83465 pontos)
LARGURA_SRA3 = int(450 * 2.83465) # 1275 pt
ALTURA_SRA3 = int(320 * 2.83465)  # 907 pt

def gerar_marcas_reportlab(largura_folha, altura_folha, marcas_corte=True, marcas_dobra=True, dobra_cruzada=False):
    """Gere um PageObject contendo as marcas de corte e dobra usando ReportLab"""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(largura_folha, altura_folha))
    
    can.setStrokeColorRGB(0, 0, 0)
    can.setLineWidth(0.5)
    
    cx = largura_folha / 2
    cy = altura_folha / 2
    comprimento_marca = 25 # aprox. 9mm
    distancia_canto = 35    # Recuo para guilhotina
    
    # 1. MARCAS DE DOBRA (Tracejadas)
    if marcas_dobra:
        can.setDash(3, 3)
        can.line(cx, altura_folha, cx, altura_folha - comprimento_marca)
        can.line(cx, 0, cx, comprimento_marca)
        
        if dobra_cruzada:
            can.line(0, cy, comprimento_marca, cy)
            can.line(largura_folha, cy, largura_folha - comprimento_marca, cy)
            
    # 2. MARCAS DE CORTE (Contínuas)
    if marcas_corte:
        can.setDash()
        # Canto Superior Esquerdo
        can.line(distancia_canto, altura_folha, distancia_canto, altura_folha - comprimento_marca)
        can.line(0, altura_folha - distancia_canto, comprimento_marca, altura_folha - distancia_canto)
        # Canto Superior Direito
        can.line(largura_folha - distancia_canto, altura_folha, largura_folha - distancia_canto, altura_folha - comprimento_marca)
        can.line(largura_folha, altura_folha - distancia_canto, largura_folha - comprimento_marca, altura_folha - distancia_canto)
        # Canto Inferior Esquerdo
        can.line(distancia_canto, 0, distancia_canto, comprimento_marca)
        can.line(0, distancia_canto, comprimento_marca, distancia_canto)
        # Canto Inferior Direito
        can.line(largura_folha - distancia_canto, 0, largura_folha - distancia_canto, comprimento_marca)
        can.line(largura_folha, distancia_canto, largura_folha - comprimento_marca, distancia_canto)
        
    can.save()
    packet.seek(0)
    marcas_reader = pypdf.PdfReader(packet)
    return marcas_reader.pages[0]

def colar_na_folha_industrial(folha_destino, pag_orig, q_larg, alt_quad, ox, oy, rodar_90=False, inverter_cabeca=False):
    """Executa o posicionamento geométrico rigoroso compensando os desvios de rotação do pypdf"""
    larg_orig = float(pag_orig.mediabox.width)
    alt_orig = float(pag_orig.mediabox.height)
    
    # Determinar escala mantendo as proporções do PDF de entrada
    if rodar_90:
        escala = min(q_larg / alt_orig, alt_quad / larg_orig) * 0.94
        w_f = alt_orig * escala
        h_f = larg_orig * escala
    else:
        escala = min(q_larg / larg_orig, alt_quad / alt_orig) * 0.94
        w_f = larg_orig * escala
        h_f = alt_orig * escala
        
    # Margens de centralização dentro do quadrante
    mx = (q_larg - w_f) / 2
    my = (alt_quad - h_f) / 2
    
    transf = Transformation()
    
    if rodar_90:
        if inverter_cabeca:
            # Roda 270 graus no sentido dos ponteiros do relógio (cabeça para o centro a partir do topo)
            transf = transf.scale(escala).rotate(270).translate(ox + mx, oy + my + h_f)
        else:
            # Roda 90 graus (cabeça para o centro a partir da base)
            transf = transf.scale(escala).rotate(90).translate(ox + mx + w_f, oy + my)
    else:
        if inverter_cabeca:
            transf = transf.scale(escala).rotate(180).translate(ox + mx + w_f, oy + my + h_f)
        else:
            transf = transf.scale(escala).translate(ox + mx, oy + my)
            
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
incluir_corte = st.sidebar.checkbox("Incluir Marcas de Corte (Cantos)", value=True)
incluir_dobra = st.sidebar.checkbox("Incluir Marcas de Dobra (Sangria)", value=True)

uploaded_file = st.file_uploader("Selecione o ficheiro PDF da Revista", type=["pdf"])

if uploaded_file is not None:
    reader = pypdf.PdfReader(uploaded_file)
    paginas = list(reader.pages)
    total_orig = len(paginas)
    
    st.info(f"Ficheiro lido! Total de páginas: **{total_orig}**")
    
    multiplo = 4 if "A4" in modo else 8
    resto = total_orig % multiplo
    if resto != 0:
        pag_em_falta = multiplo - resto
        st.warning(f"⚠️ Ajuste de Caderno: Foram geradas {pag_em_falta} páginas em branco.")
        larg_p = paginas[0].mediabox.width
        alt_p = paginas[0].mediabox.height
        for _ in range(pag_em_falta):
            paginas.append(PageObject.create_blank_page(width=larg_p, height=alt_p))
        total_orig = len(paginas)

    if st.button("Gerar Imposição Final SRA3 🚀"):
        writer = pypdf.PdfWriter()
        
        if multiplo == 4:
            # MODO A4: Duas colunas verticais
            larg_quad = LARGURA_SRA3 / 2
            alt_quad = ALTURA_SRA3
            esquerda = 0
            direita = total_orig - 1
            
            marcas = gerar_marcas_reportlab(LARGURA_SRA3, ALTURA_SRA3, incluir_corte, incluir_dobra, dobra_cruzada=False)
            
            while esquerda < direita:
                # FRENTE
                folha_frente = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                colar_na_folha_industrial(folha_frente, paginas[direita], larg_quad, alt_quad, 0, 0, rodar_90=False, inverter_cabeca=False)
                colar_na_folha_industrial(folha_frente, paginas[esquerda], larg_quad, alt_quad, larg_quad, 0, rodar_90=False, inverter_cabeca=False)
                folha_frente.merge_page(marcas)
                writer.add_page(folha_frente)
                
                esquerda += 1
                direita -= 1
                
                # VERSO
                folha_verso = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                colar_na_folha_industrial(folha_verso, paginas[esquerda], larg_quad, alt_quad, 0, 0, rodar_90=False, inverter_cabeca=False)
                colar_na_folha_industrial(folha_verso, paginas[direita], larg_quad, alt_quad, larg_quad, 0, rodar_90=False, inverter_cabeca=False)
                folha_verso.merge_page(marcas)
                writer.add_page(folha_verso)
                
                esquerda += 1
                whitespace_remover = direita -= 1
                
        else:
            # MODO A5: Grelha 2x2 Cabeça-com-Cabeça orientado para a Dobra Central Horizontal
            larg_quad = LARGURA_SRA3 / 2
            alt_quad = ALTURA_SRA3 / 2
            
            marcas_f = gerar_marcas_reportlab(LARGURA_SRA3, ALTURA_SRA3, incluir_corte, incluir_dobra, dobra_cruzada=True)
            
            for bloco in range(0, total_orig, 8):
                b_pags = paginas[bloco:bloco+8]
                
                # --- FRENTE (Face A) ---
                folha_frente = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                # Quadrantes Superiores: P5 (Esq) e P4 (Dir) -> Rotação 270° (Cabeça para baixo, apontando para o centro)
                colar_na_folha_industrial(folha_frente, b_pags[4], larg_quad, alt_quad, 0, alt_quad, rodar_90=True, inverter_cabeca=True)
                colar_na_folha_industrial(folha_frente, b_pags[3], larg_quad, alt_quad, larg_quad, alt_quad, rodar_90=True, inverter_cabeca=True)
                # Quadrantes Inferiores: P8 (Esq) e P1 (Dir) -> Rotação 90° (Cabeça para cima, apontando para o centro)
                colar_na_folha_industrial(folha_frente, b_pags[7], larg_quad, alt_quad, 0, 0, rodar_90=True, inverter_cabeca=False)
                colar_na_folha_industrial(folha_frente, b_pags[0], larg_quad, alt_quad, larg_quad, 0, rodar_90=True, inverter_cabeca=False)
                
                folha_frente.merge_page(marcas_f)
                writer.add_page(folha_frente)
                
                # --- VERSO (Face B) ---
                folha_verso = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                # Quadrantes Superiores: P3 (Esq) e P6 (Dir) -> Rotação 270° (Cabeça para baixo)
                colar_na_folha_industrial(folha_verso, b_pags[2], larg_quad, alt_quad, 0, alt_quad, rodar_90=True, inverter_cabeca=True)
                colar_na_folha_industrial(folha_verso, b_pags[5], larg_quad, alt_quad, larg_quad, alt_quad, rodar_90=True, inverter_cabeca=True)
                # Quadrantes Inferiores: P2 (Esq) e P7 (Dir) -> Rotação 90° (Cabeça para cima)
                colar_na_folha_industrial(folha_verso, b_pags[1], larg_quad, alt_quad, 0, 0, rodar_90=True, inverter_cabeca=False)
                colar_na_folha_industrial(folha_verso, b_pags[6], larg_quad, alt_quad, larg_quad, 0, rodar_90=True, inverter_cabeca=False)
                
                folha_verso.merge_page(marcas_f)
                writer.add_page(folha_verso)
                
        output_pdf = io.BytesIO()
        writer.write(output_pdf)
        output_pdf.seek(0)
        
        st.success("🎉 Imposição industrial gerada com correções geométricas absolutas!")
        st.download_button(
            label="Descarregar Ficheiro Imposição SRA3 📥",
            data=output_pdf,
            file_name="imposicao_industrial_perfeita.pdf",
            mime="application/pdf"
        )
