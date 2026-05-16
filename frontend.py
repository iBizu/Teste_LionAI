import streamlit as st
from google import genai
from google.genai import types

# ==========================================
# 1. CONFIGURAÇÃO VISUAL (TEMA WHATSAPP)
# ==========================================
st.set_page_config(page_title="WhatsApp - Lion Tech", page_icon="💬", layout="centered")

# Injetar CSS para o fundo clássico do WhatsApp e corrigir a cor do texto
st.markdown("""
<style>
    .stApp {
        background-image: url("https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png");
        background-color: #efeae2;
    }
    
    /* ATAQUE DIRETO AOS PARÁGRAFOS DO STREAMLIT */
    div[data-testid="stChatMessage"] p, 
    div[data-testid="stChatMessage"] span, 
    div[data-testid="stChatMessage"] div {
        color: #111b21 !important; 
    }
    
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Cabeçalho verde do WhatsApp
st.markdown("""
<div style="background-color: #008069; padding: 10px 20px; border-radius: 10px; margin-bottom: 20px; display: flex; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
    <div style="width: 40px; height: 40px; background-color: white; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-size: 24px; margin-right: 15px;">🦁</div>
    <div>
        <h3 style="margin: 0; color: white; font-family: sans-serif; font-size: 18px;">Lion IA (Consultor)</h3>
        <p style="margin: 0; font-size: 13px; color: #d9fdd3; font-family: sans-serif;">online</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 2. PLAYBOOK DA IA (As regras de negócio)
# ==========================================
system_instruction = """
És o Lion, o assistente comercial virtual da Lion Tech que atende via WhatsApp. O teu tom é educado, ágil e focado no cliente.
Regras da conversa:
1. Cumprimenta o utilizador de forma amigável e pergunta o seu nome e empresa.
2. Aguarda a resposta. Depois, pergunta qual é a principal dor operacional ou problema.
3. Aguarda a resposta. Em seguida, pergunta (com tato) o faturamento anual da empresa.
4. Se o faturamento for menor que 100.000, encerra a conversa educadamente dizendo que as soluções são para arquiteturas complexas.
5. Se for maior, sugere o melhor serviço (Lion Core R$2.000, Lion Agent R$3.000, ou Lion Maintenance R$500/mês). Explica brevemente o ROI.
6. Pergunta se o cliente quer agendar uma reunião.
IMPORTANTE: Faz apenas UMA pergunta de cada vez. Interage como mensagens curtas de WhatsApp.
"""

# ==========================================
# 3. INICIALIZAÇÃO DA IA E MEMÓRIA
# ==========================================
# Lê a chave diretamente do cofre seguro do Streamlit Cloud
GEMINI_KEY = st.secrets["GEMINI_KEY"]

# Só cria a conexão uma vez e guarda-a na memória para não fechar
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=GEMINI_KEY)
    
    st.session_state.chat_session = st.session_state.client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.4, 
        )
    )
    st.session_state.messages = [
        {"role": "assistant", "content": "Olá! 👋 Sou o Lion, assistente virtual da Lion Tech. Com quem tenho o prazer de falar e qual é a sua empresa?"}
    ]

# ==========================================
# 4. DESENHAR O CHAT NO ECRÃ
# ==========================================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Mensagem"):
    
    # 1. Mostra o utilizador
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Chama a IA
    with st.chat_message("assistant"):
        with st.spinner("A escrever..."):
            resposta = st.session_state.chat_session.send_message(prompt)
            st.markdown(resposta.text)
            
    # 3. Guarda na memória
    st.session_state.messages.append({"role": "assistant", "content": resposta.text})