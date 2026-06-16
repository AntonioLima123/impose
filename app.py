import streamlit as st
import pypdf
import io
from pypdf import PageObject, Transformation

# Configuração da página da plataforma
st.set_page_config(page_title="Imposição Profissional 32x45", page_icon="📖", layout="wide")

st.title("📖 Sistema de Imposição Gráfica Profissional (Formato 32x45)")
st.write("Transforme PDFs normais em folhas de imposição prontas para gráfica no formato **SRA3 (320mm x 450mm)** com múltiplos quadrantes e guias exteriores.")

# Dimensões do papel de saída: 32x45 cm em pontos PostScript (1 mm = 2.83465 pontos)
LARGURA_SRA3 = int(450 * 2.83465) # 1275 pt
ALTURA_SRA3 = int(320 * 2.83465)  # 907 pt

def desenhar_marcas_no_canvas(largura_folha, altura_folha, marcas_corte=True, marcas_dobra=True, dobra_cruzada=False):
    """Gera uma página transparente com marcas apenas nas extremidades exteriores (sangria)"""
    overlay = PageObject.create_blank_page(width=largura_folha, height=altura_folha)
    comandos = []
    
    # Linha fina de 0.5 pontos em tom cinza escuro
    comandos.append("0.5 w")
    comandos.append("0.2 0.2 0.2 RG")
    
    cx = largura_folha / 2
    cy = altura_folha / 2
    comprimento_marca = 25 # tamanho das guias nas bordas (aprox. 9mm)
    
    # 1. MARCAS DE DOBRA (Apenas nas pontas exteriores, em tracejado)
    if marcas_dobra:
        comandos.append("[3 3] 0 d") # Ativa o tracejado para vincos
        
        # Dobra Vertical (Eixo Central)
        comandos.append(f"{cx} {altura_folha} m {cx} {altura_folha - comprimento_marca} l")
        comandos.append(f"{cx} 0 m {cx} {comprimento_marca} l")
        
        if dobra_cruzada:
            # Dobra Horizontal (Eixo Central para formato A5)
            comandos.append(f"0 {cy} m {comprimento_marca} {cy} l")
            comandos.append(f"{largura_folha} {cy} m {largura_folha - comprimento_marca} {cy} l")
        comandos.append("S")
        
    # 2. MARCAS DE CORTE / REFILE (Linhas contínuas nos quatro cantos do papel)
    if marcas_corte:
        comandos.append("[] 0 d") # Desativa o tracejado (linha contínua)
        distancia_canto = 40       # Recuo estratégico para guiar a lâmina
        
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

def colar_na_folha(folha_destino, pag_orig, larg_quad, alt_quad, ox, oy, rodar_180=False):
    """Calcula a transformação geométrica e injeta a página de forma compatível com qualquer pypdf"""
    larg_orig = float(pag_orig.mediabox.width)
    alt_orig = float(pag_orig.mediabox.height)
    
    # Escala proporcional para ajustar a página original ao quadrante da folha gráfica
    escala_x = larg_quad / larg_orig
    escala_y = alt_quad / alt_orig
    escala = min(escala_x, escala_y) * 0.92 # Redução de 8% para margem física de segurança e sangria
    
    # Centralização interna
    margem_x = (larg_quad - (larg_orig * escala)) / 2
    margem_y = (alt_quad - (alt_orig * escala)) / 2
    
    if rodar_180:
        # Orientação cabeça-com-cabeça: escala, inverte na origem e projeta para o topo do quadrante
        transf = (
            Transformation()
            .scale(escala)
            .rotate(180)
            .translate(ox + larg_quad - margem_x, oy + alt_quad - margem_y)
        )
    else:
        # Orientação normal de leitura base
        transf = (
            Transformation()
            .scale(escala)
            .translate(ox + margem_x, oy + margem_y)
        )
    
    # Estratégia Universal contra o TypeError: criamos uma folha temporária isolada,
    # aplicamos a transformação nela e fazemos o merge limpo. Evita falhas no Streamlit Cloud.
    pag_temporaria = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
    pag_temporaria.merge_page(pag_orig)
    pag_temporaria.add_transformation(transf)
    
    # Adiciona à folha master do PDF
    folha_destino.merge_page(pag_temporaria)

# Configurações na Barra Lateral
st.sidebar.header("⚙️ Definições de Imposição")
modo = st.sidebar.selectbox("Tipo de Caderno", ["Revista A4 ou Menor (Caderno de 4 Páginas)", "Revista A5 ou Menor (Caderno de 8 Páginas - Dobra Cruzada)"])
incluir_corte = st.sidebar.checkbox("Incluir Marcas de Corte nos Cantos", value=True)
incluir_dobra = st.sidebar.checkbox("Incluir Marcas de Dobra Periféricas", value=True)

uploaded_file = st.file_uploader("Selecione o ficheiro PDF original", type=["pdf"])

if uploaded_file is not None:
    try:
        reader = pypdf.PdfReader(uploaded_file)
        paginas = list(reader.pages)
        total_orig = len(paginas)
        
        st.info(f"Ficheiro carregado com sucesso! Total de páginas originais: **{total_orig}**")
        
        # Define o fator múltiplo dependendo da paginação de máquina escolhida
        multiplo = 4 if "4 Páginas" in modo else 8
        resto = total_orig % multiplo
        if resto != 0:
            pag_em_falta = multiplo - resto
            st.warning(f"⚠️ Nota de Ajuste: Foram adicionadas {pag_em_falta} página(s) em branco no final para o caderno ficar completo.")
            larg_p = paginas[0].mediabox.width
            alt_p = paginas[0].mediabox.height
            for _ in range(pag_em_falta):
                paginas.append(PageObject.create_blank_page(width=larg_p, height=alt_p))
            total_orig = len(paginas)

        if st.button("Gerar Imposição Gráfica 32x45 🚀"):
            writer = pypdf.PdfWriter()
            
            if multiplo == 4:
                # 2 páginas lógicas por face (Metade esquerda e metade direita)
                larg_quad = LARGURA_SRA3 / 2
                alt_quad = ALTURA_SRA3
                esquerda = 0
                direita = total_orig - 1
                
                while esquerda < direita:
                    # --- FOLHA FRENTE (Face A) ---
                    folha_frente = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                    colar_na_folha(folha_frente, paginas[direita], larg_quad, alt_quad, 0, 0, rodar_180=False)
                    colar_na_folha(folha_frente, paginas[esquerda], larg_quad, alt_quad, larg_quad, 0, rodar_180=False)
                    
                    marcas = desenhar_marcas_no_canvas(LARGURA_SRA3, ALTURA_SRA3, incluir_corte, incluir_dobra, dobra_cruzada=False)
                    folha_frente.merge_page(marcas)
                    writer.add_page(folha_frente)
                    
                    esquerda += 1
                    direita -= 1
                    
                    # --- FOLHA VERSO (Face B) ---
                    folha_verso = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                    colar_na_folha(folha_verso, paginas[esquerda], larg_quad, alt_quad, 0, 0, rodar_180=False)
                    colar_na_folha(folha_verso, paginas[direita], larg_quad, alt_quad, larg_quad, 0, rodar_180=False)
                    
                    folha_verso.merge_page(marcas)
                    writer.add_page(folha_verso)
                    
                    esquerda += 1
                    direita -= 1
                    
            else:
                # 4 páginas lógicas por face (Grelha Industrial 2x2 com Dobra Cruzada)
                larg_quad = LARGURA_SRA3 / 2
                alt_quad = ALTURA_SRA3 / 2
                
                for bloco in range(0, total_orig, 8):
                    b_pags = paginas[bloco:bloco+8]
                    
                    # --- FRENTE DO CADERNO (Face A) ---
                    folha_frente = PageObject.create_blank_page(width=LARGURA_SRA3, height=ALTURA_SRA3)
                    # Linhas Superiores - Invertidas cabeça-com-cabeça (180°)
                    colar_na_folha(folha_frente, b_pags[4], larg_quad, alt_quad, 0, alt_quad, rodar_180=True)          # Topo Esq (Págs
