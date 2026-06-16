import streamlit as st
import pypdf
import io
from pypdf import PageObject

# Configuração da página da plataforma
st.set_page_config(page_title="Gerador de Cadernos para Revista", page_icon="📖", layout="centered")

st.title("📖 Organizador de PDF para Revista Agrafada")
st.write("Insira o seu PDF original. A ferramenta irá fundir as páginas lado a lado no formato correto para impressão direta em Frente e Verso.")

def juntar_duas_paginas(pag_esquerda, pag_direita):
    """Função auxiliar para colocar duas páginas verticais lado a lado numa folha horizontal"""
    largura = pag_esquerda.mediabox.width
    altura = pag_esquerda.mediabox.height
    
    # Cria uma nova página em branco com o dobro da largura (Formato Paisagem)
    nova_pagina = PageObject.create_blank_page(width=largura * 2, height=altura)
    
    # Funde as duas páginas na nova folha
    nova_pagina.merge_page(pag_esquerda)
    nova_pagina.merge_translated_page(pag_direita, largura, 0)
    
    return nova_pagina

# Upload do Ficheiro
uploaded_file = st.file_uploader("Escolha o seu arquivo PDF", type=["pdf"])

if uploaded_file is not None:
    try:
        # Ler o PDF enviado
        reader = pypdf.PdfReader(uploaded_file)
        paginas = list(reader.pages)
        total_paginas = len(paginas)
        
        st.info(f"O seu PDF original tem *{total_paginas} páginas*.")
        
        # Correção automática: Se não for múltiplo de 4, criamos páginas em branco
        enquanto_resto = total_paginas % 4
        if  enquanto_resto != 0:
            paginas_a_adicionar = 4 - enquanto_resto
            st.warning(f"⚠️ O documento tem {total_paginas} páginas (não é múltiplo de 4). A aplicação vai adicionar automaticamente {paginas_a_adicionar} página(s) em branco no final para permitir o vinco correto.")
            
            largura_padrao = paginas[0].mediabox.width
            altura_padrao = paginas[0].mediabox.height
            
            for _ in range(paginas_a_adicionar):
                pag_em_branco = PageObject.create_blank_page(width=largura_padrao, height=altura_padrao)
                paginas.append(pag_em_branco)
            
            total_paginas = len(paginas)

        # Botão para processar o PDF
        if st.button("Converter para Impressão 🚀"):
            writer = pypdf.PdfWriter()
            
            esquerda = 0
            direita = total_paginas - 1
            
            # Loop de imposição física
            while esquerda < direita:
                # --- FOLHA FRENTE (Ex: Pág Última [Esquerda] + Pág 1 [Direita]) ---
                folha_frente = juntar_duas_paginas(paginas[direita], paginas[esquerda])
                writer.add_page(folha_frente)
                
                esquerda += 1
                direita -= 1
                
                # --- FOLHA VERSO (Ex: Pág 2 [Esquerda] + Pág Penúltima [Direita]) ---
                # Isto garante que a Página 2 é impressa exatamente nas "costas" da Página 1
                folha_verso = juntar_duas_paginas(paginas[esquerda], paginas[direita])
                writer.add_page(folha_verso)
                
                esquerda += 1
                direita -= 1
            
            # Guardar o ficheiro em memória
            output_pdf = io.BytesIO()
            writer.write(output_pdf)
            output_pdf.seek(0)
            
            st.success("🎉 PDF gerado e montado horizontalmente com sucesso!")
            
            # Botão de download
            st.download_button(
                label="Baixar PDF Paginado 📥",
                data=output_pdf,
                file_name="revista_pronta_para_impressao.pdf",
                mime="application/pdf"
            )
            
            # Instruções simplificadas porque o Python já fez o trabalho difícil!
            st.markdown("""
            ---
            ### ⚙️ Como imprimir o arquivo gerado (Muito mais fácil agora!):
            1. Abra o PDF descarregado (vai notar que as páginas já estão deitadas e juntas).
            2. Vá a **Imprimir** (Ctrl + P).
            3. Defina o Tamanho do Papel como **Normal / Tamanho Real** (Não use a opção Múltiplo!).
            4. Ative a impressão em **Frente e Verso** (Duplex).
            5. **[CRUCIAL]** Nas definições do Frente e Verso, escolha **"Virar na borda mais curta"** (Short-edge binding).
            """)
            
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
