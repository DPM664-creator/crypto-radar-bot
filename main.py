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
    'mad_apes_gambles',
    'TheDonsCalls',
    'TheSolitairePrestige',
    'gubbinscalls',
    'mad_apes',
    'sadcatgamble',
    'ghastlygems',
    'uranusX100',
    'ramcalls'
]

REDES = ["solana", "ethereum", "bsc", "base"]
SENT_CAS_FILE = "sent_cas.json"

def carregar_cas_enviados():
    """Carrega lista de CAs já enviados"""
    if os.path.exists(SENT_CAS_FILE):
        try:
            with open(SENT_CAS_FILE, 'r') as f:
                data = json.load(f)
                return data.get('cas_enviados', [])
        except:
            return []
    return []

def salvar_cas_enviados(cas_enviados):
    """Salva lista de CAs enviados localmente"""
    with open(SENT_CAS_FILE, 'w') as f:
        json.dump({'cas_enviados': cas_enviados}, f, indent=2)

def commitar_no_github():
    """Envia o arquivo atualizado para o GitHub"""
    if not all([PAT_TOKEN, REPO_OWNER, REPO_NAME]):
        print("⚠️ Tokens do GitHub não configurados")
        return
    
    try:
        with open(SENT_CAS_FILE, 'r') as f:
            content = f.read()
        
        content_b64 = base64.b64encode(content.encode()).decode()
        
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{SENT_CAS_FILE}"
        headers = {
            'Authorization': f'token {PAT_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Tenta pegar o SHA atual
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # Arquivo existe, atualiza
            sha = response.json()['sha']
            data = {
                'message': f'Update sent CAs - {datetime.now().strftime("%H:%M:%S")}',
                'content': content_b64,
                'sha': sha
            }
            response = requests.put(url, headers=headers, json=data)
        elif response.status_code == 404:
            # Arquivo não existe, cria
            data = {
                'message': f'Create sent CAs file - {datetime.now().strftime("%H:%M:%S")}',
                'content': content_b64
            }
            response = requests.put(url, headers=headers, json=data)
        
        if response.status_code in [200, 201]:
            print("✅ Memória salva no GitHub com sucesso!")
        else:
            print(f"❌ Erro ao salvar no GitHub: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro no commit: {e}")

async def verificar_canais_telegram(ca_address):
    if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH]):
        print("⚠️ Credenciais API Telegram não configuradas")
        return 0, []
    
    canais_que_mencionaram = []
    
    try:
        client = TelegramClient('primeape_session', TELEGRAM_API_ID, TELEGRAM_API_HASH)
        await client.start()
        
        for canal in CANAIS_ALPHA:
            try:
                async for message in client.iter_messages(canal, limit=50):
                    if ca_address.lower() in message.text.lower():
                        if canal not in canais_que_mencionaram:
                            canais_que_mencionaram.append(canal)
                        break
            except Exception as e:
                print(f"  ⚠️ Erro ao verificar @{canal}: {e}")
                continue
        
        await client.disconnect()
        
    except Exception as e:
        print(f"❌ Erro na conexão Telegram: {e}")
    
    return len(canais_que_mencionaram), canais_que_mencionaram

def enviar_alerta_telegram(mensagem):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("⚠️ Credenciais do Bot Telegram não configuradas")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": mensagem,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            print("✅ Alerta enviado!")
        else:
            print(f"❌ Erro: {response.text}")
    except Exception as e:
        print(f"❌ Erro: {e}")

def buscar_pares_dexscreener():
    print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Buscando pares...")
    pares_validos = []
    
    for rede in REDES:
        try:
            url_search = f"https://api.dexscreener.com/latest/dex/search?q={rede}"
            response = requests.get(url_search, timeout=10)
            data = response.json()
            pares = data.get('pairs', [])
            
            for par in pares[:100]:
                if aplicar_filtros(par):
                    pares_validos.append(par)
                    
        except Exception as e:
            print(f"  ⚠️ Erro {rede}: {e}")
            
    return pares_validos

def aplicar_filtros(par):
    liquidez = par.get('liquidity', {}).get('usd', 0)
    if not liquidez or liquidez < 5000:
        return False
    
    market_cap = par.get('fdv', 0) or par.get('marketCap', 0)
    if not market_cap or market_cap < 10000:
        return False
    
    volume_24h = par.get('volume', {}).get('h24', 0)
    if volume_24h > 0:
        ratio = volume_24h / market_cap
        if ratio > 0.10:
            return False
    
    pump_1h = par.get('priceChange', {}).get('h1', 0)
    if pump_1h > 10.0:
        return False
    
    if volume_24h < 1000:
        return False
        
    return True

def classificar_oportunidade(num_canais):
    if num_canais >= 2:
        return 1, "🥇 HIGH CONFIDENCE"
    elif num_canais == 1:
        return 2, "🥈 OPPORTUNITY"
    else:
        return 3, "🥉 HIDDEN GEM"

def formatar_alerta(par, nivel, canais_mencionados):
    token_symbol = par.get('baseToken', {}).get('symbol', 'Unknown')
    ca = par.get('pairAddress', 'N/A')
    rede = par.get('chainId', 'N/A').upper()
    liquidez = par.get('liquidity', {}).get('usd', 0)
    pump_1h = par.get('priceChange', {}).get('h1', 0)
    volume_24h = par.get('volume', {}).get('h24', 0)
    market_cap = par.get('fdv', 0) or par.get('marketCap', 0)
    price = par.get('priceUsd', '0')
    
    try:
        price_formatted = f"${float(price):.8f}" if price and price != '0' else "N/A"
    except:
        price_formatted = "N/A"
    
    emojis = {1: "🥇", 2: "🥈", 3: ""}
    titulos = {1: "HIGH CONFIDENCE", 2: "OPPORTUNITY", 3: "HIDDEN GEM"}
    descricoes = {
        1: "Multiple alpha channels talking!",
        2: "One alpha channel spotted it!",
        3: "Nobody talking yet! Pure alpha!"
    }
    
    dex_link = f"[DexScreener](https://dexscreener.com/{rede.lower()}/{ca})"
    
    mensagem = (
        f"{emojis[nivel]} *PRIMEAPE 7 - {titulos[nivel]}* {emojis[nivel]}\n"
        f"\n"
        f"📌 *{descricoes[nivel]}*\n"
        f"\n"
        f"🥇 *Token:* #{token_symbol} ({token_symbol})\n"
        f"*CA:* `{ca}`\n"
        f"*Chain:* {rede}\n"
        f"*Price:* {price_formatted}\n"
        f"*Market Cap:* ${market_cap:,.2f}\n"
        f"*Liquidity:* ${liquidez:,.2f}\n"
        f"*Vol 24h:* ${volume_24h:,.2f}\n"
        f"*Pump 1h:* {pump_1h}%\n"
        f"\n"
        f"{dex_link}\n"
        f"\n"
        f"⚠️ _DYOR!_"
    )

    return mensagem

async def main():
    print(" PrimeApe 7 Iniciado...")
    
    # 1. Carregar memória
    cas_enviados = carregar_cas_enviados()
    print(f"📋 {len(cas_enviados)} CAs já enviados anteriormente")
    
    # 2. Buscar novos
    oportunidades = buscar_pares_dexscreener()
    print(f"🎯 {len(oportunidades)} oportunidades encontradas nos filtros!")
    
    # 3. Filtrar repetidos
    oportunidades_novas = [op for op in oportunidades if op.get('pairAddress') not in cas_enviados]
    print(f"✨ {len(oportunidades_novas)} oportunidades NOVAS (sem repetição)")
    
    # 4. Ordenar e enviar top 3
    oportunidades_novas.sort(key=lambda x: x.get('liquidity', {}).get('usd', 0) + x.get('volume', {}).get('h24', 0), reverse=True)
    
    if oportunidades_novas:
        novos_cas = []
        for i, op in enumerate(oportunidades_novas[:3], 1):
            token = op.get('baseToken', {}).get('symbol', 'Unknown')
            ca = op.get('pairAddress', 'N/A')
            
            print(f"\n[{i}/3] {token}")
            
            num_canais, canais_mencionados = await verificar_canais_telegram(ca)
            nivel, _ = classificar_oportunidade(num_canais)
            
            mensagem = formatar_alerta(op, nivel, canais_mencionados)
            enviar_alerta_telegram(mensagem)
            
            novos_cas.append(ca)
            
            import time
            time.sleep(2)
        
        # 5. Salvar na memória e commitar no GitHub
        cas_enviados.extend(novos_cas)
        salvar_cas_enviados(cas_enviados)
        commitar_no_github()
        print(f"\n💾 {len(novos_cas)} novos CAs salvos na memória")
    else:
        print("\n Nenhuma oportunidade nova nesta rodada")
        enviar_alerta_telegram("*PrimeApe 7*\n\n🔍 No new opportunities found.\n\n_The radar is still active!_")

    print("\n✅ Fim.")

if __name__ == "__main__":
    asyncio.run(main())
