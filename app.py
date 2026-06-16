import streamlit as st
import pypdf
import io

# Configuração da página da plataforma
st.set_page_config(page_title="Gerador de Cadernos para Revista", page_icon="📖", layout="centered")

st.title("📖 Organizador de PDF para Revista Agrafada")
st.write("Insira o seu PDF original e a ferramenta irá reorganizar as páginas na sequência correta para impressão em modo *Múltiplo (2x1) Paisagem*.")

# Upload do Ficheiro
uploaded_file = st.file_uploader("Escolha o seu arquivo PDF (O total de páginas deve ser múltiplo de 4)", type=["pdf"])

if uploaded_file is not None:
    try:
        # Ler o PDF enviado
        reader = pypdf.PdfReader(uploaded_file)
        total_paginas = len(reader.pages)
        
        st.info(f"O seu PDF tem *{total_paginas} páginas*.")
        
        # Validação da regra de ouro das revistas (Múltiplos de 4)
        if total_paginas % 4 != 0:
            st.error(f"Erro: O número de páginas ({total_paginas}) não é múltiplo de 4. Adicione páginas em branco ao seu documento antes de enviar.")
        else:
            # Botão para processar o PDF
            if st.button("Converter para Impressão 🚀"):
                writer = pypdf.PdfWriter()
                
                # Algoritmo de imposição para revista intercalada: 32, 1, 2, 31...
                sequencia = []
                esquerda = 0
                direita = total_paginas - 1
                
                while esquerda < direita:
                    # Par da Frente (Ex: 32 e 1)
                    sequencia.append(direita)
                    sequencia.append(esquerda)
                    esquerda += 1
                    direita -= 1
                    
                    # Par do Verso (Ex: 2 e 31)
                    sequencia.append(esquerda)
                    sequencia.append(direita)
                    esquerda += 1
                    direita -= 1

                # Organizar o novo PDF com base na sequência calculada
                for num_pagina in sequencia:
                    writer.add_page(reader.pages[num_pagina])
                
                # Guardar o ficheiro em memória para disponibilizar para download
                output_pdf = io.BytesIO()
                writer.write(output_pdf)
                output_pdf.seek(0)
                
                st.success("🎉 PDF reorganizado com sucesso!")
                
                # Botão para o utilizador descarregar o resultado final
                st.download_button(
                    label="Baixar PDF Paginado 📥",
                    data=output_pdf,
                    file_name="revista_pronta_para_impressao.pdf",
                    mime="application/pdf"
                )
                
                # Instruções de uso para o utilizador final
                st.markdown("""
                ---
                ### ⚙️ Como imprimir o arquivo gerado:
                1. Abra o PDF descarregado no *Adobe Acrobat*.
                2. Pressione Ctrl + P.
                3. Selecione a opção *Múltiplo*.
                4. Configure as páginas por folha como *Personalizado: 2 × 1*.
                5. Defina a Orientação como *Paisagem*.
                6. Ative o Frente e Verso escolhendo *"Virar na borda mais curta"*.
                """)
                
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo: {e}")