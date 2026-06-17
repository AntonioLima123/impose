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
        can.line(largura_folha, altura_folha - afastamento, largura_folha - comprimento_marca, altura_folha - afastamento)
        # Canto Inferior Esquerdo
        can.line(afastamento, 0, afastamento, comprimento_marca)
        can.line(0, afastamento, comprimento_marca, afastamento)
        # Canto Inferior Direito
        can.line(largura_folha - afastamento, 0, largura_folha - slams if 'slams' in locals() else afastamento, comprimento_marca)
        can.line(
