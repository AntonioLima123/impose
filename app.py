import streamlit as st
import pypdf
import io
from pypdf import PageObject, Transformation

# Configuração da página da plataforma
st.set_page_config(page_title="Imposição Profissional 32x45", page_icon="📖", layout="wide")

st.title("📖 Sistema de Imposição Gráfica Profissional (Formato 32x45)")
st.write("Gere esquemas de imposição reais para gráfica em formato **SRA3 (320mm x 450mm)** com marcas periféricas e rotações automáticas.")

# Dimensões do papel de saída SRA3 em pontos (1 mm = 2.83465 pontos)
LARGURA_SRA3 = int(450 * 2.83465) # 1275 pt
ALTURA_SRA3 = int(320 * 2.83465)  # 907 pt

def desenhar_marcas_no_canvas(largura_folha, altura_folha, marcas_corte=True, marcas_dobra=True, dobra_cruzada=False):
    """Gera uma página transparente contendo as regras vetoriais de corte e dobra na sangria"""
    overlay = PageObject.create_blank_page(width=largura_folha, height=altura_folha)
    comandos = []
    
    # Linha fina (0.5 pt) em preto puro de registo
    comandos.append("0.5 w")
    comandos.append("0 0 0 RG")
    
    cx = largura_folha / 2
    cy = altura_folha / 2
    comprimento_marca = 25 # tamanho das guias (aprox. 9mm)
    
    # 1. MARCAS DE DOBRA (Apenas nas pontas exteriores, em tracejado)
    if marcas_dobra:
        comandos.append("[3 3] 0 d") # Ativa o tracejado para vincos
        
        # Dobra Vertical Central (comum a A4 e A5)
        comandos.append(f"{cx} {altura_folha} m {cx} {altura_folha - comprimento_marca} l")
        comandos.append(f"{cx} 0 m {cx} {comprimento_marca} l")
        
        if dobra_cruzada:
            # Dobra Horizontal Central (exclusiva do caderno de 8 pág. A5)
            comandos.append(f"0 {cy} m {comprimento_marca} {cy} l")
            comandos.append(f"{largura_folha} {cy} m {largura_folha - comprimento_marca} {cy} l")
        comandos.append("S")
        
    # 2. MARCAS DE CORTE / REFILE (Linhas nos quatro cantos externos)
    if marcas_corte:
        comandos.append("[] 0 d") # Desativa o tracejado (linha contínua)
        distancia_canto = 35       # Alinhamento do limite físico da guilhotina
        
        # Canto Superior Esquerdo
        comandos.append(f"{distancia_canto} {altura_folha} m {distancia_canto} {altura_folha - comprimento_marca} l")
        comandos.append(f"0 {altura_folha - distancia_canto} m {comprimento_marca} {altura_folha - distancia_canto} l")
        
        # Canto Superior Direito
        comandos.append(f"{largura_folha - distancia_canto} {altura_folha} m {largura_folha - distancia_canto} {altura_folha - comprimento_marca} l")
        comandos.append(f"{largura_folha} {altura_folha - distancia_canto} m {largura_folha - comprimento_marca} {distancia_canto} l")
        
        # Canto Inferior Esquerdo
        comandos.append(f"{distancia_canto} 0 m {distancia_canto} {comprimento_marca} l")
        comandos.append(f"0 {distancia_canto} m {comprimento_marca} {distancia_canto} l")
        
        # Canto Inferior Direito
        comandos.append(f"{largura_folha - distancia_canto} 0 m {largura_folha - distancia_canto} {comprimento_marca} l")
        comandos.append(f"{largura_folha} {distancia_canto} m {largura_folha - comprimento_marca} {distancia_canto} l")
        
        comandos.append("S")
        
    if comandos:
        conteudo_grafico = "\n".join(comandos).encode('utf-8')
        # Injeção compatível e forçada através de stream limpo no PDF
        try:
            from pypdf import ContentStream
            overlay._contents = ContentStream(conteudo_grafico, overlay.pdf)
        except:
            overlay.set_contents(pypdf.generic.DecodedStreamObject(conteudo_grafico))
            
    return overlay

def colar_na_folha_industrial(folha_destino, pag_orig, q_larg, alt_quad, ox, oy, rodar_90=False, inverter_cabeca=False):
    """Executa a rotação complexa de encaixe mantendo a consistência dos eixos da folha"""
    larg_orig = float(pag_orig.mediabox.width)
    alt_orig = float(pag_orig.mediabox.height)
    
    # 1. Determinar Escala Proporcional correta
    if rodar_90:
        escala = min(q_larg / alt_orig, alt_quad / larg_orig) * 0.92
        w_f = alt_orig * escala
        h_f = larg_orig * escala
    else:
        escala = min(q_larg / larg_orig, alt_quad / alt_orig) * 0.92
        w_f = larg_orig * escala
        h_f = alt_orig * escala
        
    mx = (q_larg - w_f) / 2
    my = (alt_quad - h_f) / 2
    
    # 2. Construir Matriz de Transformação Isolada
    transf = Transformation().scale(escala)
    
    if rodar_90:
        if inverter_cabeca:
            # Roda -90° (Cabeça orientada para a linha de dobra central horizontal)
            transf = transf.rotate(-90).translate(ox + mx, oy + my + h_f)
        else:
            # Roda +90° (Cabeça orientada para a linha de dobra central horizontal)
            transf = transf.rotate(90).translate(ox + mx + w_f, oy + my)
    else:
        if inverter_cabeca:
            # Inversão total de 180° (para esquemas especiais)
            transf = transf.rotate(180).translate(ox + mx + w_f, oy + my + h_f)
        else:
            # Posição Padrão Vertical
            transf = transf.translate(ox + mx, oy + my)
            
    # Criação da película intermediária para garantir que o merge não corrompe os quadrantes vizinhos
    pag_temp = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
    pag_temp.merge_page(pag_orig)
    pag_temp.add_transformation(transf)
    
    folha_destino.merge_page(pag_temp)

# --- INTERFACE DE CONTROLO ---
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
    
    st.info(f"Ficheiro lido! Total de páginas identificadas: **{total_orig}**")
    
    # Definir o divisor do caderno
    multiplo = 4 if "A4" in modo else 8
    resto = total_orig % multiplo
    if resto != 0:
        pag_em_falta = multiplo - resto
        st.warning(f"⚠️ Ajuste de Caderno: Foram geradas {pag_em_falta} páginas em branco para respeitar a imposição de {multiplo} págs.")
        larg_p = paginas[0].mediabox.width
        alt_p = paginas[0].mediabox.height
        for _ in range(pag_em_falta):
            paginas.append(PageObject.create_blank_page(width=larg_p, height=alt_p))
        total_orig = len(paginas)

    # Preview Gráfico Dinâmico no Painel
    st.subheader("🗺️ Mapa Planeado para a Dobra Física (Folha 1)")
    c1, c2 = st.columns(2)
    if multiplo == 4:
        with c1: st.info("**FRENTE (Face A)**\n\n Lado Esq: Pág Ultima  |  Lado Dir: Pág 1")
        with c2: st.info("**VERSO (Face B)**\n\n Lado Esq: Pág 2  |  Lado Dir: Pág Penúltima")
    else:
        with c1: st.info("**FRENTE (Face A) - Dobra Cruzada**\n\n[ Pág 5 ⬇️ (Invertida)]  [ Pág 4 ⬇️ (Invertida)]\n\n[ Pág 8 ⬆️ (Normal)]  [ Pág 1 ⬆️ (Normal)]")
        with c2: st.info("**VERSO (Face B) - Dobra Cruzada**\n\n[ Pág 3 ⬇️ (Invertida)]  [ Pág 6 ⬇️ (Invertida)]\n\n[ Pág 2 ⬆️ (Normal)]  [ Pág 7 ⬆️ (Normal)]")

    if st.button("Gerar Imposição Final SRA3 🚀"):
        writer = pypdf.PdfWriter()
        
        if multiplo == 4:
            # MODO A4: Duas páginas verticais dispostas lado a lado na folha 32x45
            larg_quad = LARGURA_SRA3 / 2
            alt_quad = ALTURA_SRA3
            esquerda = 0
            direita = total_orig - 1
            
            marcas = desenhar_marcas_no_canvas(LARGURA_SRA3, ALTURA_SRA3, incluir_corte, incluir_dobra, dobra_cruzada=False)
            
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
                colar_na_folha_industrial(folha_verso, paginas[direita], larg_quad, alt_quad, larg_quad, 0, rodar_180=False, inverter_cabeca=False)
                folha_verso.merge_page(marcas)
                writer.add_page(folha_verso)
                
                esquerda += 1
                direita -= 1
                
        else:
            # MODO A5: Quatro páginas deitadas (Grelha 2x2) com Dobra Cruzada Cabeça-com-Cabeça
            larg_quad = LARGURA_SRA3 / 2
            alt_quad = ALTURA_SRA3 / 2
            
            marcas_f = desenhar_marcas_no_canvas(LARGURA_SRA3, ALTURA_SRA3, incluir_corte, incluir_dobra, dobra_cruzada=True)
            
            for bloco in range(0, total_orig, 8):
                b_pags = paginas[bloco:bloco+8]
                
                # --- FRENTE (Face A) ---
                folha_frente = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                # Quadrantes Superiores (P5 e P4) -> Rodadas -90° (Cabeça orientada para o CENTRO da folha)
                colar_na_folha_industrial(folha_frente, b_pags[4], larg_quad, alt_quad, 0, alt_quad, rodar_90=True, inverter_cabeca=True)
                colar_na_folha_industrial(folha_frente, b_pags[3], larg_quad, alt_quad, larg_quad, alt_quad, rodar_90=True, inverter_cabeca=True)
                # Quadrantes Inferiores (P8 e P1) -> Rodadas +90° (Cabeça orientada para o CENTRO da folha)
                colar_na_folha_industrial(folha_frente, b_pags[7], larg_quad, alt_quad, 0, 0, rodar_90=True, inverter_cabeca=False)
                colar_na_folha_industrial(folha_frente, b_pags[0], larg_quad, alt_quad, larg_quad, 0, rodar_90=True, inverter_cabeca=False)
                
                folha_frente.merge_page(marcas_f)
                writer.add_page(folha_frente)
                
                # --- VERSO (Face B) ---
                folha_verso = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                # Quadrantes Superiores (P3 e P6) -> Rodadas -90° (Cabeça orientada para o CENTRO da folha)
                colar_na_folha_industrial(folha_verso, b_pags[2], larg_quad, alt_quad, 0, alt_quad, rodar_90=True, inverter_cabeca=True)
                colar_na_folha_industrial(folha_verso, b_pags[5], larg_quad, alt_quad, larg_quad, alt_quad, rodar_90=True, inverter_cabeca=True)
                # Quadrantes Inferiores (P2 e P7) -> Rodadas +90° (Cabeça orientada para o CENTRO da folha)
                colar_na_folha_industrial(folha_verso, b_pags[1], larg_quad, alt_quad, 0, 0, rodar_90=True, inverter_cabeca=False)
                colar_na_folha_industrial(folha_verso, b_pags[6], larg_quad, alt_quad, larg_quad, 0, rodar_90=True, inverter_cabeca=False)
                
                folha_verso.merge_page(marcas_f)
                writer.add_page(folha_verso)
                
        output_pdf = io.BytesIO()
        writer.write(output_pdf)
        output_pdf.seek(0)
        
        st.success("🎉 Imposição corrigida e marcas reconstruídas com sucesso!")
        st.download_button(
            label="Descarregar Ficheiro Imposição SRA3 📥",
            data=output_pdf,
            file_name="imposicao_industrial_perfeita.pdf",
            mime="application/pdf"
        )
