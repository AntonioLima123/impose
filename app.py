import streamlit as st
import pypdf
import io
from pypdf import PageObject, Transformation

# Configuração da página da plataforma
st.set_page_config(page_title="Imposição Profissional 32x45", page_icon="📖", layout="wide")

st.title("📖 Sistema de Imposição Gráfica Profissional (Formato 32x45)")
st.write("Transforme PDFs normais em folhas de imposição prontas para gráfica no formato **SRA3 (320mm x 450mm)** com marcas limpas na sangria exterior.")

# Dimensões do papel de saída: 32x45 cm em pontos
LARGURA_SRA3 = int(450 * 2.83465) # 1275 pt
ALTURA_SRA3 = int(320 * 2.83465)  # 907 pt

def desenhar_marcas_no_canvas(largura_folha, altura_folha, marcas_corte=True, marcas_dobra=True, dobra_cruzada=False):
    """
    Gera uma página transparente com marcas apenas nas extremidades exteriores (sangria),
    garantindo que NADA cruza ou interfere com o meio da revista impressa.
    """
    overlay = PageObject.create_blank_page(width=largura_folha, height=altura_folha)
    comandos = []
    
    # Linha fina de 0.5 pontos em tom cinza escuro/preto de registo
    comandos.append("0.5 w")
    comandos.append("0.2 0.2 0.2 RG")
    
    cx = largura_folha / 2
    cy = altura_folha / 2
    comprimento_marca = 25 # tamanho das guias nas bordas (aprox. 9mm)
    
    # 1. MARCAS DE DOBRA (Apenas nas pontas exteriores, em tracejado)
    if marcas_dobra:
        comandos.append("[3 3] 0 d") # Ativa o tracejado
        
        # Dobra Vertical (Eixo Central) - Apenas no topo e na base exterior
        comandos.append(f"{cx} {altura_folha} m")
        comandos.append(f"{cx} {altura_folha - comprimento_marca} l")
        comandos.append(f"{cx} 0 m")
        comandos.append(f"{cx} {comprimento_marca} l")
        
        if dobra_cruzada:
            # Dobra Horizontal (Eixo Central para A5) - Apenas nas laterais esquerda e direita exteriores
            comandos.append(f"0 {cy} m")
            comandos.append(f"{comprimento_marca} {cy} l")
            comandos.append(f"{largura_folha} {cy} m")
            comandos.append(f"{largura_folha - comprimento_marca} {cy} l")
        comandos.append("S")
        
    # 2. MARCAS DE CORTE / REFILE (Linhas contínuas nos cantos)
    if marcas_corte:
        comandos.append("[] 0 d") # Desativa o tracejado (linha contínua)
        distancia_canto = 40       # Recuo para marcar os cantos do papel
        
        # Canto Superior Esquerdo
        comandos.append(f"{distancia_canto} {altura_folha} m {distancia_canto} {altura_folha - comprimento_marca} l")
        comandos.append(f"0 {altura_folha - distancia_canto} m {comprimento_marca} {altura_folha - distancia_canto} l")
        
        # Canto Superior Direito
        comandos.append(f"{largura_folha - distancia_canto} {altura_folha} m {largura_folha - distancia_canto} {altura_folha - comprimento_marca} l")
        comandos.append(f"{largura_folha} {altura_folha - distancia_canto} m {largura_folha - comprimento_marca} {altura_folha - distancia_canto} l")
        
        # Canto Inferior Esquerdo
        comandos.append(f"{distancia_canto} 0 m {distancia_canto} {comprimento_marca} l")
        comandos.append(f"0 {distancia_canto} m {comprimento_marca} {distancia_canto} l")
        
        # Canto Inferior Direito
        comandos.append(f"{largura_folha - distancia_canto} 0 m {largura_folha - distancia_canto} {comprimento_marca} l")
        comandos.append(f"{largura_folha} {distancia_canto} m {largura_folha - comprimento_marca} {distancia_canto} l")
        
        comandos.append("S")
        
    if comandos:
        conteudo_grafico = "\n".join(comandos).encode('utf-8')
        try:
            from pypdf import ContentStream
            overlay._contents = ContentStream(conteudo_grafico, overlay.pdf)
        except:
            pass
            
    return overlay

def ajustar_e_posicionar(pag_orig, larg_destino, alt_destino, ox, oy, rodar_180=False):
    larg_orig = float(pag_orig.mediabox.width)
    alt_orig = float(pag_orig.mediabox.height)
    
    escala_x = larg_destino / larg_orig
    escala_y = alt_destino / alt_orig
    escala = min(escala_x, escala_y) * 0.93 # Margem ligeiramente maior para garantir espaço seguro para o refile
    
    margem_x = (larg_destino - (larg_orig * escala)) / 2
    margem_y = (alt_destino - (alt_orig * escala)) / 2
    
    if rodar_180:
        transf = Transformation().scale(escala).translate(margem_x, margem_y).rotate(180).translate(ox + larg_destino - margem_x, oy + alt_destino - margem_y)
    else:
        transf = Transformation().scale(escala).translate(ox + margem_x, oy + margem_y)

    quadrante = PageObject.create_blank_page(width=larg_destino, height=alt_destino)
    quadrante.merge_page(pag_orig)
    quadrante.add_transformation(transf)
    return quadrante

# Interface do Utilizador
st.sidebar.header("⚙️ Definições de Imposição")
modo = st.sidebar.selectbox("Tipo de Caderno", ["Revista A4 ou Menor (Caderno de 4 Páginas)", "Revista A5 ou Menor (Caderno de 8 Páginas - Dobra Cruzada)"])
incluir_corte = st.sidebar.checkbox("Incluir Marcas de Corte nos Cantos", value=True)
incluir_dobra = st.sidebar.checkbox("Incluir Marcas de Dobra Periféricas", value=True)

uploaded_file = st.file_uploader("Selecione o ficheiro PDF original", type=["pdf"])

if uploaded_file is not None:
    reader = pypdf.PdfReader(uploaded_file)
    paginas = list(reader.pages)
    total_orig = len(paginas)
    
    st.info(f"Ficheiro carregado com sucesso! Total de páginas: **{total_orig}**")
    
    multiplo = 4 if "4 Páginas" in modo else 8
    resto = total_orig % multiplo
    if resto != 0:
        pag_em_falta = multiplo - resto
        st.warning(f"⚠️ Ajuste Automático: Foram adicionadas {pag_em_falta} página(s) em branco para perfazer o caderno de {multiplo} páginas.")
        larg_p = paginas[0].mediabox.width
        alt_p = paginas[0].mediabox.height
        for _ in range(pag_em_falta):
            paginas.append(PageObject.create_blank_page(width=larg_p, height=alt_p))
        total_orig = len(paginas)

    if st.button("Gerar Imposição Gráfica 32x45 🚀"):
        writer = pypdf.PdfWriter()
        
        if multiplo == 4:
            larg_quad = LARGURA_SRA3 / 2
            alt_quad = ALTURA_SRA3
            esquerda = 0
            direita = total_orig - 1
            
            while esquerda < direita:
                # FRENTE
                folha_frente = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                p_esq = ajustar_e_posicionar(paginas[direita], larg_quad, alt_quad, 0, 0)
                p_dir = ajustar_e_posicionar(paginas[esquerda], larg_quad, alt_quad, larg_quad, 0)
                folha_frente.merge_page(p_esq)
                folha_frente.merge_page(p_dir)
                
                marcas = desenhar_marcas_no_canvas(LARGURA_SRA3, ALTURA_SRA3, incluir_corte, incluir_dobra, dobra_cruzada=False)
                folha_frente.merge_page(marcas)
                writer.add_page(folha_frente)
                
                esquerda += 1
                direita -= 1
                
                # VERSO
                folha_verso = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                p_esq = ajustar_e_posicionar(paginas[esquerda], larg_quad, alt_quad, 0, 0)
                p_dir = ajustar_e_posicionar(paginas[direita], larg_quad, alt_quad, larg_quad, 0)
                folha_verso.merge_page(p_esq)
                folha_verso.merge_page(p_dir)
                folha_verso.merge_page(marcas)
                writer.add_page(folha_verso)
                
                esquerda += 1
                direita -= 1
                
        else:
            larg_quad = LARGURA_SRA3 / 2
            alt_quad = ALTURA_SRA3 / 2
            
            for bloco in range(0, total_orig, 8):
                b_pags = paginas[bloco:bloco+8]
                
                # FRENTE (Grelha 2x2)
                folha_frente = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                te = ajustar_e_posicionar(b_pags[4], larg_quad, alt_quad, 0, alt_quad, rodar_180=True)
                td = ajustar_e_posicionar(b_pags[3], larg_quad, alt_quad, larg_quad, alt_quad, rodar_180=True)
                be = ajustar_e_posicionar(b_pags[7], larg_quad, alt_quad, 0, 0, rodar_180=False)
                bd = ajustar_e_posicionar(b_pags[0], larg_quad, alt_quad, larg_quad, 0, rodar_180=False)
                
                folha_frente.merge_page(te)
                folha_frente.merge_page(td)
                folha_frente.merge_page(be)
                folha_frente.merge_page(bd)
                
                marcas_f = desenhar_marcas_no_canvas(LARGURA_SRA3, ALTURA_SRA3, incluir_corte, incluir_dobra, dobra_cruzada=True)
                folha_frente.merge_page(marcas_f)
                writer.add_page(folha_frente)
                
                # VERSO (Grelha 2x2)
                folha_verso = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                te_v = ajustar_e_posicionar(b_pags[2], larg_quad, alt_quad, 0, alt_quad, rodar_180=True)
                td_v = ajustar_e_posicionar(b_pags[5], larg_quad, alt_quad, larg_quad, alt_quad, rodar_180=True)
                be_v = ajustar_e_posicionar(b_pags[1], larg_quad, alt_quad, 0, 0, rodar_180=False)
                bd_v = ajustar_e_posicionar(b_pags[6], larg_quad, alt_quad, larg_quad, 0, rodar_180=False)
                
                folha_verso.merge_page(te_v)
                folha_verso.merge_page(td_v)
                folha_verso.merge_page(be_v)
                folha_verso.merge_page(bd_v)
                folha_verso.merge_page(marcas_f)
                writer.add_page(folha_verso)
                
        output_pdf = io.BytesIO()
        writer.write(output_pdf)
        output_pdf.seek(0)
        
        st.success("🎉 Imposição industrial SRA3 limpa gerada com sucesso!")
        st.download_button(
            label="Descarregar Ficheiro para Gráfica 📥",
            data=output_pdf,
            file_name="imposicao_limpa_32x45.pdf",
            mime="application/pdf"
        )
