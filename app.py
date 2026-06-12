import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from deep_translator import GoogleTranslator
import math
import io

# Configuração da página
st.set_page_config(
    page_title="Extrator & Tradutor com OCR",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Extrator, Tradutor e OCR de Livros Escaneados")
st.markdown("Esta versão detecta automaticamente páginas escaneadas e aplica OCR para extrair e traduzir o texto.")

# --- BARRA LATERAL ---
st.sidebar.header("📁 Upload do Livro")
uploaded_file = st.sidebar.file_uploader("Escolha o arquivo PDF", type=["pdf"])

# --- FUNÇÕES AUXILIARES COM OCR ---
@st.cache_data(show_spinner="Analisando estrutura do PDF...")
def obter_total_paginas(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    total = len(doc)
    doc.close()
    return total

def processar_pagina_com_ocr(file_bytes, num_pagina):
    """Tenta extrair o texto nativo. Se falhar, renderiza a página como imagem e aplica OCR."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pagina = doc.load_page(num_pagina - 1)
    
    # 1. Tenta extração de texto nativa
    texto = pagina.get_text()
    
    # 2. Se o texto nativo for muito curto ou inexistente, ativa o OCR
    if not texto or len(texto.strip()) < 10:
        # Renderiza a página como uma imagem (matriz de pixels)
        # O zoom_x e zoom_y aumentam a resolução (DPI) para o OCR ler melhor
        zoom = 2  
        matriz = fitz.Matrix(zoom, zoom)
        pix = pagina.get_pixmap(matrix=matriz)
        
        # Converte os bytes do pixmap para uma imagem PIL
        img_data = pix.tobytes("png")
        imagem_pil = Image.open(io.BytesIO(img_data))
        
        # Executa o OCR buscando conteúdos em inglês e português
        try:
            texto = pytesseract.image_to_string(imagem_pil, lang="por+eng")
            if not texto.strip():
                texto = "[OCR executado, mas nenhum texto legível foi detectado nesta página]"
        except Exception as e:
            texto = f"[Erro ao executar OCR]: {str(e)}\nCertifique-se de que o packages.txt está configurado no GitHub."
            
    doc.close()
    return texto

def traduzir_texto_seguro(texto, idioma_destino="pt"):
    if "[OCR executado" in texto or "[Erro" in texto:
        return texto
    try:
        tradutor = GoogleTranslator(source='auto', target=idioma_destino)
        paragrafos = texto.split('\n')
        traduzido = []
        for para in paragrafos:
            if para.strip():
                txt_limpo = para if len(para) < 4500 else para[:4500]
                traduzido.append(tradutor.translate(txt_limpo))
            else:
                traduzido.append("")
        return "\n".join(traduzido)
    except Exception as e:
        return f"[Erro na Tradução]: {str(e)}"

# --- FLUXO PRINCIPAL ---
if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    
    total_paginas = obter_total_paginas(file_bytes)
    st.sidebar.metric(label="Total de Páginas", value=total_paginas)
    
    # Divisão em 4 blocos
    tamanho_bloco = math.ceil(total_paginas / 4)
    divisao_blocos = []
    for i in range(4):
        inicio = (i * tamanho_bloco) + 1
        fim = min((i + 1) * tamanho_bloco, total_paginas)
        if inicio <= total_paginas:
            divisao_blocos.append((inicio, fim))

    st.sidebar.subheader("🧩 Escolha a Parte do Livro")
    opcoes_blocos = [f"Parte {i+1} (Págs. {b[0]} a {b[1]})" for i, b in enumerate(divisao_blocos)]
    bloco_selecionado_idx = st.sidebar.selectbox("Selecione:", range(len(opcoes_blocos)), format_func=lambda x: opcoes_blocos[x])
    
    p_inicio, p_fim = divisao_blocos[bloco_selecionado_idx]
    
    # Interface de Leitura Lado a Lado
    tab_leitura = st.tabs(["📖 Modo Leitura Lado a Lado (Com OCR Dinâmico)"])[0]
    
    with tab_leitura:
        # Cria a lista de páginas pertencentes ao bloco selecionado
        paginas_do_bloco = list(range(p_inicio, p_fim + 1))
        pagina_atual = st.select_slider("Escolha a página para ler:", options=paginas_do_bloco)
        
        # Executa o processamento/OCR apenas para a página selecionada na tela (Garante performance fluida!)
        with st.spinner(f"Processando e aplicando OCR na página {pagina_atual}..."):
            conteudo_pagina = processar_pagina_com_ocr(file_bytes, pagina_atual)
        
        # Opções de Tradução na Barra Lateral
        st.sidebar.subheader("🌐 Tradução")
        precisa_traduzir = st.sidebar.checkbox("Habilitar Tradução", value=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"#### 📄 Texto Extraído (OCR) - Página {pagina_atual}")
            st.text_area(label="O", value=conteudo_pagina, height=500, key=f"o_{pagina_atual}", label_visibility="collapsed")
            
        with col2:
            st.markdown(f"#### 🇧🇷 Tradução para PT - Página {pagina_atual}")
            if precisa_traduzir:
                with st.spinner("Traduzindo texto extraído..."):
                    texto_traduzido_pag = traduzir_texto_seguro(conteudo_pagina, "pt")
                st.text_area(label="T", value=texto_traduzido_pag, height=500, key=f"t_{pagina_atual}", label_visibility="collapsed")
            else:
                st.info("Marque 'Habilitar Tradução' na barra lateral.")
else:
    st.info("👋 Pronto para começar! Faça o upload de um livro em PDF na barra lateral.")