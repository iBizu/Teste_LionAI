import datetime
import sqlite3
import requests
import os.path
from fastapi import FastAPI
from pydantic import BaseModel

# Importações do Gemini
from google import genai
from google.genai import types

# Novas Importações do Google Calendar
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ==========================================
# 1. CONFIGURAÇÕES E CHAVES
# ==========================================
GEMINI_KEY = "CHAVE_GEMINI"
TRELLO_KEY = "CHAVE_TRELLO"
TRELLO_TOKEN = (
    "CHAVE_DO_TRELLO"
)
LISTA_QUENTES = "6a04b16d2ce0415146ae8e16"
LISTA_BAIXA = "6a04b173244cc08fc124794e"

client = genai.Client(api_key=GEMINI_KEY)
app = FastAPI(title="IA Comercial Lion")

# Permissão que a IA precisa (Apenas ler e escrever eventos na agenda)
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


# ==========================================
# 2. INTEGRAÇÃO GOOGLE CALENDAR
# ==========================================
def agendar_no_calendar(nome_cliente):
    """Autentica na conta Google e cria um evento para amanhã às 14:00."""
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:

            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        # Guarda o novo token para não pedir login na próxima vez
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    # Constrói o serviço do Google Calendar
    service = build("calendar", "v3", credentials=creds)

    # Prepara as datas (Amanhã das 14:00 às 14:30, formato ISO)
    amanha = datetime.datetime.now() + datetime.timedelta(days=1)
    inicio = amanha.replace(hour=14, minute=0, second=0).isoformat() + "-03:00"
    fim = amanha.replace(hour=14, minute=30, second=0).isoformat() + "-03:00"

    evento_config = {
        "summary": f"🦁 Reunião Lion Tech: {nome_cliente}",
        "description": "Reunião de alinhamento e apresentação do diagnóstico gerado pela IA.",
        "start": {"dateTime": inicio, "timeZone": "America/Sao_Paulo"},
        "end": {"dateTime": fim, "timeZone": "America/Sao_Paulo"},
    }

    # Envia o evento para a agenda oficial
    evento_criado = (
        service.events().insert(calendarId="primary", body=evento_config).execute()
    )
    print(f"✅ Evento criado com sucesso no Calendar: {evento_criado.get('htmlLink')}")

    return amanha.strftime("%d/%m/%Y às %H:%M")


# ==========================================
# 3. BASE DE DADOS (SQLite - Memória e Logs)
# ==========================================
def init_db():
    conn = sqlite3.connect("comercial.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS leads 
                 (id INTEGER PRIMARY KEY, nome TEXT, decisao TEXT)""")
    conn.close()


def registrar_log(nome, decisao):
    conn = sqlite3.connect("comercial.db")
    conn.execute("INSERT INTO leads (nome, decisao) VALUES (?, ?)", (nome, decisao))
    conn.commit()
    conn.close()


# ==========================================
# 4. MODELO DE ENTRADA E MOTOR DE IA
# ==========================================
class Lead(BaseModel):
    nome: str
    empresa: str
    cargo: str
    faturamento: float
    problema: str


def processar_com_gemini(nome, empresa, problema):
    system_instruction = """
    És um consultor comercial da empresa Lion. A tua missão é diagnosticar dores operacionais e converter leads.
    Tom de voz: Profissional, assertivo, consultivo e focado em ROI. SEM gírias.
    Não prometas descontos acima de 10%.
    
    SERVIÇOS DISPONÍVEIS:
    1. Lion Core: Implementação de infraestrutura de dados (R$ 2.000,00).
    2. Lion Agent: Criação de agentes autônomos (R$ 3.000,00).
    3. Lion Maintenance: Suporte mensal e otimização (R$ 500,00/mês).
    """
    prompt = f"O cliente {nome} da empresa {empresa} relatou este problema: '{problema}'. Com base nos nossos serviços, responde sugerindo o melhor serviço e cria um parágrafo argumentando sobre o ROI da automação."

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system_instruction),
        )
        return response.text
    except Exception as e:
        print(f"❌ Erro na IA: {e}")
        return "Neste momento, a nossa IA de diagnóstico está em atualização. A nossa equipa entrará em contacto em breve!"


# ==========================================
# 5. ROTA PRINCIPAL (Endpoints FastAPI)
# ==========================================
@app.post("/whatsapp")
async def handle_lead(data: Lead):
    print(f"\n📥 Recebido lead de {data.nome} ({data.empresa})")

    # Qualificação
    if data.faturamento < 100000:
        requests.post(
            f"https://api.trello.com/1/cards?idList={LISTA_BAIXA}&key={TRELLO_KEY}&token={TRELLO_TOKEN}&name=Frio: {data.nome}"
        )
        registrar_log(data.nome, "Desqualificado - Faturamento < 100k")

        mensagem_fria = (
            f"Olá, {data.nome}. Agradeço o seu interesse. "
            f"Atualmente, as soluções da Lion Tech são desenhadas para arquiteturas complexas "
            f"e empresas com faturamento acima de R$ 100 mil, devido ao custo de implementação "
            f"e infraestrutura necessários. No seu momento atual com a {data.empresa} recomendo ferramentas de automação plug-and-play de baixo custo. Manteremos seu contato em nossa base para futuras atualizações de produtos voltados ao varejo de menor escala. Desejamos muito sucesso e "
            f"esperamos poder colaborar no futuro!"
        )

        return {"resposta_whatsapp": mensagem_fria}

    # Inteligência (Gemini)
    print("🧠 A processar análise com Gemini...")
    resposta_ia = processar_com_gemini(data.nome, data.empresa, data.problema)

    # Integração Trello
    print("📋 A criar cartão no Trello...")
    requests.post(
        f"https://api.trello.com/1/cards?idList={LISTA_QUENTES}&key={TRELLO_KEY}&token={TRELLO_TOKEN}&name=Quente: {data.nome}&desc={resposta_ia}"
    )

    # Integração Google Calendar
    print("📅 A agendar reunião no Google Calendar...")
    horario_formatado = agendar_no_calendar(data.nome)

    registrar_log(data.nome, "Qualificado - Trello e Agenda Atualizados")

    # Resposta Final
    resposta_final = f"{resposta_ia}\n\nPara avançarmos, reservei espaço na minha agenda para uma reunião de 30 minutos no dia {horario_formatado}. Podemos confirmar?"

    return {"resposta_whatsapp": resposta_final}


init_db()
