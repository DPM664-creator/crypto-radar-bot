import requests
import os
import asyncio
import json
import base64
from datetime import datetime
from telethon import TelegramClient

# --- CONFIGURAÇÕES ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
PAT_TOKEN = os.getenv('PAT_TOKEN')
REPO_OWNER = os.getenv('REPO_OWNER')
REPO_NAME = os.getenv('REPO_NAME')

CANAIS_ALPHA = [
    'mad_apes_gambles', 'TheDonsCalls', 'TheSolitairePrestige',
    'gubbinscalls', 'mad_apes', 'sadcatgamble',
    'ghastlygems', 'uranusX100', 'ramcalls'
]

# BSC incluído e priorizado
REDES = ["solana", "ethereum", "bsc", "base"]
SENT_CAS_FILE = "sent_cas.json"
PULSE_CONTROL_FILE = "last_pulse_hour.txt"

# --- FUNÇÕES DE MEMÓRIA ---
def carregar_cas_enviados():
    if os.path.exists(SENT_CAS_FILE):
        try:
            with open(SENT_CAS_FILE, 'r') as f:
                return json.load(f).get('cas_enviados', [])
        except: return []
    return []

def salvar_cas_enviados(cas_enviados):
    with open(SENT_CAS_FILE, 'w') as f:
        json.dump({'cas_enviados': cas_enviados}, f, indent=2)

def commitar_no_github():
    if not all([PAT_TOKEN, REPO_OWNER, REPO_NAME]):
        print("️ Tokens do GitHub não configurados")
        return
    
    for arquivo in [SENT_CAS_FILE, PULSE_CONTROL_FILE]:
        if not os.path.exists(arquivo): continue
        try:
            with open(arquivo, 'r') as f: content = f.read()
            content_b64 = base64.b64encode(content.encode()).decode()
            url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{arquivo}"
            headers = {'Authorization': f'token {PAT_TOKEN}', 'Accept': 'application/vnd.github.v3+json'}
            
            response = requests.get(url, headers=headers)
            sha = response.json()['sha']
