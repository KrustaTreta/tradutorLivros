import streamlit as st
from pypdf import PdfReader
from deep_translator import GoogleTranslator
import math
import time

# Configuração da página
st.set_page_config(
    page_title="Extrator & Tradutor - Alta Performance",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Extrator e Tradutor de Livros (Otimizado)")
st.markdown("Otimizado para PDFs grandes e pesados. O livro foi segmentado para garantir estabilidade.")

# --- BARRA LATERAL ---
st.sidebar.header("📁 Upload do Livro")
uploaded_file = st.sidebar.file_uploader("Escolha o arquivo PDF", type=["pdf"])

# --- FUNÇÕES AUXILIARES OTIMIZADAS (Usando PyPDF para velocidade) ---
@st.cache_data(show_spinner="Analisando estrutura do PDF...")
def analisar_pdf_rapido(file_bytes):
    """Abre o arquivo na memória uma única vez, conta páginas e extrai metadados."""
    reader = PdfReader(file_bytes)
    return len(reader.pages)

def extrair_texto_pypdf(file_bytes, pagina_inicio, pagina_fim):
    """Extração de alta performance para blocos específicos."""
    reader = PdfReader(file_bytes)
    paginas_texto = []
    
    # Índices ajustados para 0-indexed do PyPDF
    for idx in range(pagina_inicio - 1, min(pagina_fim, len(reader.pages))):
        try:
            pagina = reader.pages[idx]
            texto = pagina.extract_text()
            if texto and texto.strip():
                paginas_texto.append({"pagina": idx + 1, "conteudo": texto})
            else:
                paginas_texto.append({"pagina": idx + 1, "conteudo": f"[Página {idx + 1} vazia ou contém apenas imagens]"})
        except Exception:
            paginas_texto.append({"pagina": idx + 1, "conteudo": f"[Erro ao ler a página {idx + 1}]"})
    return paginas_texto

def traduzir_texto_seguro(texto, idioma_destino="pt"):
    try:
        tradutor = GoogleTranslator(source='auto', target=idioma_destino)
        paragrafos = texto.split('\n')
        traduzido = []
        for para in paragrafos:
            if para.strip():
                # Corta parágrafos absurdamente longos se houver erro de formatação no PDF
                txt_limpo = para if len(para) < 4500 else para[:4500]
                traduzido.append(tradutor.translate(txt_limpo))
            else:
                traduzido.append("")
        return "\n".join(traduzido)
    except Exception as e:
        return f"[Erro de Conexão na Tradução]: {str(e)}"

# --- FLUXO PRINCIPAL ---
if uploaded_file is not None:
    # Lemos os bytes do arquivo uma vez para alimentar as funções com cache estável
    file_bytes = uploaded_file.getvalue()
    
    # 1. Conta as páginas usando a função cacheada ultra rápida
    total_paginas = analisar_pdf_rapido(file_bytes)
    st.sidebar.metric(label="Total de Páginas", value=total_paginas)
    
    # Divisão em 4 blocos
    tamanho_bloco = math.ceil(total_paginas / 4)
    divisao_blocos = []
    for i in range(4):
        inicio = (i * tamanho_bloco) + 1
        fim = min((i + 1) * tamanho_bloco, total_paginas)
        if inicio <= total_paginas:
            divisao_blocos.append((inicio, fim))

    # Interface de Seleção de Bloco
    st.sidebar.subheader("🧩 Escolha a Parte do Livro")
    opcoes_blocos = [f"Parte {i+1} (Págs. {b[0]} a {b[1]})" for i, b in enumerate(divisao_blocos)]
    bloco_selecionado_idx = st.sidebar.selectbox("Selecione:", range(len(opcoes_blocos)), format_func=lambda x: opcoes_blocos[x])
    
    p_inicio, p_fim = divisao_blocos[bloco_selecionado_idx]
    
    # 2. Extração sob demanda apenas do bloco selecionado
    @st.cache_data(show_spinner=f"Processando páginas {p_inicio} a {p_fim}...")
    def obter_dados_bloco(bytes_data, inicio, fim):
        return extrair_texto_pypdf(bytes_data, inicio, fim)
    
    dados_bloco = obter_dados_bloco(file_bytes, p_inicio, p_fim)
    
    if dados_bloco:
        texto_completo_bloco = "\n\n".join([f"--- PÁGINA {p['pagina']} ---\n{p['conteudo']}" for p in dados_bloco])
        
        # Opções de Tradução
        st.sidebar.subheader("🌐 Tradução")
        precisa_traduzir = st.sidebar.checkbox("Habilitar Tradução")
        
        texto_traduzido_completo_bloco = ""
        modo_traducao = "Apenas Página Selecionada"
        
        if precisa_traduzir:
            modo_traducao = st.sidebar.radio("Escopo da Tradução:", ["Apenas Página Selecionada", "Traduzir Parte Atual Completa"])
            
            if modo_traducao == "Traduzir Parte Atual Completa":
                @st.cache_data(show_spinner=None)
                def traduzir_bloco_com_progresso(dados_do_bloco):
                    traduzido_paginas = []
                    progresso_bar = st.progress(0, text="Traduzindo páginas...")
                    total_itens = len(dados_do_bloco)
                    
                    for index, p in enumerate(dados_do_bloco):
                        percentual = (index + 1) / total_itens
                        progresso_bar.progress(percentual, text=f"Traduzindo página {p['pagina']}...")
                        
                        # Se a página não tiver texto extraível, pula a chamada da API
                        if "vazia ou contém apenas imagens" in p["conteudo"]:
                            txt_traduzido = p["conteudo"]
                        else:
                            txt_traduzido = traduzir_texto_seguro(p["conteudo"], "pt")
                            
                        traduzido_paginas.append(f"--- PÁGINA {p['pagina']} (Traduzida) ---\n{txt_traduzido}")
                        time.sleep(0.1)
                        
                    progresso_bar.empty()
                    return "\n\n".join(traduzido_paginas)
                
                texto_traduzido_completo_bloco = traduzir_bloco_com_progresso(dados_bloco)
        
        # --- ABAS DE INTERFACE ---
        tab_leitura, tab_download = st.tabs(["📖 Modo Leitura Lado a Lado", "💾 Exportar Arquivos"])
        
        with tab_leitura:
            lista_paginas_bloco = [p["pagina"] for p in dados_bloco]
            pagina_atual = st.select_slider("Escolha a página para ler:", options=lista_paginas_bloco)
            
            dados_pagina_atual = next(p for p in dados_bloco if p["pagina"] == pagina_atual)
            conteudo_pagina = dados_pagina_atual["conteudo"]
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 📄 Original - Página {pagina_atual}")
                st.text_area(label="O", value=conteudo_pagina, height=500, key=f"o_{pagina_atual}", label_visibility="collapsed")
                
            with col2:
                st.markdown(f"#### 🇧🇷 Tradução - Página {pagina_atual}")
                if precisa_traduzir:
                    if modo_traducao == "Apenas Página Selecionada":
                        texto_traduzido_pag = traduzir_texto_seguro(conteudo_pagina, "pt")
                    else:
                        texto_traduzido_pag = traduzir_texto_seguro(conteudo_pagina, "pt")
                    st.text_area(label="T", value=texto_traduzido_pag, height=500, key=f"t_{pagina_atual}", label_visibility="collapsed")
                else:
                    st.info("Marque 'Habilitar Tradução' na barra lateral.")
                    
        with tab_download:
            st.subheader("📥 Baixar Arquivos de Texto (.txt)")
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    label="Baixar Texto Original (Bloco)",
                    data=texto_completo_bloco,
                    file_name=f"bloco_original_{p_inicio}_{p_fim}.txt",
                    mime="text/plain"
                )
            with c2:
                if precisa_traduzir and modo_traducao == "Traduzir Parte Atual Completa":
                    st.download_button(
                        label="Baixar Texto Traduzido (Bloco)",
                        data=texto_traduzido_completo_bloco,
                        file_name=f"bloco_traduzido_{p_inicio}_{p_fim}.txt",
                        mime="text/plain"
                    )
                else:
                    st.warning("Ative 'Traduzir Parte Atual Completa' para baixar a tradução deste bloco.")
else:
    st.info("👋 Pronto para começar! Faça o upload de um livro em PDF na barra lateral.")