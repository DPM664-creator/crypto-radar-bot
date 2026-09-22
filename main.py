import requests
import os
import asyncio
import json
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# --- CONFIGURAÇÕES ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_SESSION_STRING = os.getenv('TELEGRAM_SESSION_STRING')
PAT_TOKEN = os.getenv('PAT_TOKEN')
REPO_OWNER = os.getenv('REPO_OWNER')
REPO_NAME = os.getenv('REPO_NAME')

# Lista será carregada automaticamente do arquivo
CANAIS_ALPHA = []

REDES = ["solana", "ethereum", "bsc", "base"]
SENT_CAS_FILE = "sent_cas.json"
PULSE_CONTROL_FILE = "last_pulse_hour.txt"
MARKET_PULSE_FILE = "last_market_pulse.txt"
CHANNELS_FILE = "channels_list.json"

TOKENS_NATIVOS = [
    'SOL', 'ETH', 'BNB', 'MATIC', 'AVAX', 'FTM', 'ARB', 'OP', 'BASE',
    'USDC', 'USDT', 'DAI', 'WETH', 'WSOL', 'WBNB', 'WBTC'
]

# --- FUNÇÕES DE MEMÓRIA ---
def carregar_cas_enviados():
    if os.path.exists(SENT_CAS_FILE):
        try:
            with open(SENT_CAS_FILE, 'r') as f:
                return json.load(f).get('cas_enviados', [])
        except:
            return []
    return []

def salvar_cas_enviados(cas_enviados):
    with open(SENT_CAS_FILE, 'w') as f:
        json.dump({'cas_enviados': cas_enviados}, f, indent=2)

def carregar_canais():
    """Carrega lista de canais do arquivo channels_list.json"""
    global CANAIS_ALPHA
    
    if os.path.exists(CHANNELS_FILE):
        try:
            with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
                canais = json.load(f)
            
            # Extrai apenas os identificadores (username ou título)
            CANAIS_ALPHA = [c['identificador'] for c in canais]
            print(f"📋 {len(CANAIS_ALPHA)} canais carregados do arquivo")
            return CANAIS_ALPHA
        except Exception as e:
            print(f"⚠️ Erro ao carregar canais: {e}")
            return []
    else:
        print("⚠️ Arquivo channels_list.json não encontrado")
        return []

def commitar_no_github():
    if not all([PAT_TOKEN, REPO_OWNER, REPO_NAME]):
        return
    
    for arquivo in [SENT_CAS_FILE, PULSE_CONTROL_FILE, MARKET_PULSE_FILE]:
        if not os.path.exists(arquivo):
            continue
        try:
            import base64
            with open(arquivo, 'r', encoding='utf-8') as f:
                content = f.read()
            content_b64 = base64.b64encode(content.encode()).decode()
            url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{arquivo}"
            headers = {'Authorization': f'token {PAT_TOKEN}', 'Accept': 'application/vnd.github.v3+json'}
            
            response = requests.get(url, headers=headers)
            sha = None
            if response.status_code == 200:
                sha = response.json()['sha']
            
            data = {'message': f'Update {arquivo}', 'content': content_b64}
            if sha:
                data['sha'] = sha
            
            requests.put(url, headers=headers, json=data)
        except:
            pass

# --- MARKET PULSE (a cada 3h) ---
def get_preco_global():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,binancecoin&vs_currencies=usd&include_24hr_change=true"
        resp = requests.get(url, timeout=10).json()
        return {
            'BTC': resp['bitcoin'], 'ETH': resp['ethereum'],
            'SOL': resp['solana'], 'BNB': resp['binancecoin']
        }
    except:
        return None

def enviar_market_pulse():
    print(" Sending Market Pulse...")
    precos = get_preco_global()
    
    msg = "🦍 *PRIMEAPE 7 - MARKET PULSE*\n\n"
    
    if precos:
        msg += "📊 *Global Market:*\n"
        for k, v in [('BTC', precos['BTC']), ('ETH', precos['ETH']), ('SOL', precos['SOL']), ('BNB', precos['BNB'])]:
            change = v.get('usd_24h_change', 0)
            emoji = "" if change >= 0 else "🔴"
            msg += f"{emoji} *{k}:* ${v['usd']:,.2f} ({change:+.1f}%)\n"
    
    msg += "\n📡 *Radar Status:*\n"
    msg += "• Scanning: SOL, ETH, BSC, BASE\n"
    msg += "• Filters: MC $500-$2M | Liq $500-$200k | Vol $5k+ | <14 days\n"
    msg += f"• Active Channels: {len(CANAIS_ALPHA)}\n"
    msg += "\n🔔 _Turn on notifications!_"
    
    enviar_alerta_telegram(msg)
    
    with open(MARKET_PULSE_FILE, 'w') as f:
        f.write(str(datetime.now().hour))

def verificar_market_pulse():
    hora_atual = datetime.now().hour
    
    if not os.path.exists(MARKET_PULSE_FILE):
        return True
    
    try:
        ultima_hora = int(open(MARKET_PULSE_FILE).read())
        diferenca = (hora_atual - ultima_hora) % 24
        
        if diferenca >= 3:
            return True
    except:
        return True
    
    return False

def verificar_pulse_horario():
    hora_atual = datetime.now().hour
    hora_salva = -1
    
    if os.path.exists(PULSE_CONTROL_FILE):
        try:
            hora_salva = int(open(PULSE_CONTROL_FILE).read())
        except:
            pass
    
    if hora_atual != hora_salva:
        with open(PULSE_CONTROL_FILE, 'w') as f:
            f.write(str(hora_atual))
        return True
    return False

# --- FUNÇÕES PRINCIPAIS ---
async def verificar_canais_telegram(ca_address):
    if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_STRING]):
        print("️ Session string not configured")
        return 0, []
    
    canais_que_mencionaram = []
    try:
        client = TelegramClient(StringSession(TELEGRAM_SESSION_STRING), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print("⚠️ Session invalid")
            return 0, []
        
        print(f"🔍 Scanning {len(CANAIS_ALPHA)} channels...")
        
        for canal in CANAIS_ALPHA:
            try:
                entity = await client.get_entity(canal)
                
                async for message in client.iter_messages(entity, limit=50):
                    if ca_address.lower() in message.text.lower():
                        canal_nome = entity.username if entity.username else entity.title
                        if canal_nome not in canais_que_mencionaram:
                            canais_que_mencionaram.append(canal_nome)
                        break
                        
            except Exception as e:
                continue
        
        await client.disconnect()
    except Exception as e:
        print(f"❌ Telegram connection error: {e}")
    
    return len(canais_que_mencionaram), canais_que_mencionaram

def enviar_alerta_telegram(mensagem, reply_markup=None, parse_mode="Markdown"):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHANNEL_ID, 
        "text": mensagem, 
        "parse_mode": parse_mode, 
        "disable_web_page_preview": True
    }
    if reply_markup:
        data["reply_markup"] = reply_markup.to_json()
    
    try:
        resp = requests.post(url, json=data, timeout=10)
        if resp.status_code == 200:
            print("✅ Alert sent!")
    except Exception as e:
        print(f"❌ Error: {e}")

def get_gmgn_link(ca, rede):
    rede_map = {'solana': 'sol', 'ethereum': 'eth', 'bsc': 'bsc', 'base': 'base'}
    rede_short = rede_map.get(rede.lower(), 'sol')
    return f"https://gmgn.ai/{rede_short}/token/{ca}"

def get_dexscreener_link(ca, rede):
    return f"https://dexscreener.com/{rede.lower()}/{ca}"

def aplicar_filtros(par):
    liq = par.get('liquidity', {}).get('usd', 0)
    mc = par.get('fdv', 0) or par.get('marketCap', 0)
    vol = par.get('volume', {}).get('h24', 0)
    pump_1h = par.get('priceChange', {}).get('h1', 0)
    pump_24h = par.get('priceChange', {}).get('h24', 0)
    
    base_token = par.get('baseToken', {})
    symbol = base_token.get('symbol', '').upper()
    
    if symbol in TOKENS_NATIVOS:
        return False
    
    if not mc or mc < 500 or mc > 2000000:
        return False
    
    if not liq or liq < 500 or liq > 200000:
        return False
    
    if vol < 5000:
        return False
    
    if pump_24h < 0 or pump_24h > 300:
        return False
    
    if pump_1h < -50:
        return False
    
    if vol / mc < 0.05 or vol / mc > 3.0:
        return False
    
    pair_address = par.get('pairAddress', '')
    if not pair_address or len(pair_address) < 10:
        return False
    
    pair_created_at = par.get('pairCreatedAt', 0)
    if pair_created_at:
        created_timestamp = pair_created_at / 1000
        now_timestamp = datetime.now().timestamp()
        age_days = (now_timestamp - created_timestamp) / 86400
        
        if age_days > 14:
            return False
    
    return True

def buscar_pares_dexscreener():
    print(f" [{datetime.now().strftime('%H:%M:%S')}] Scanning pairs...")
    pares_validos = []
    total_brutos = 0
    
    for rede in REDES:
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={rede}"
            data = requests.get(url, timeout=10).json()
            pares = data.get('pairs', [])
            total_brutos += len(pares)
            print(f"  🔍 {rede.upper()}: {len(pares)} raw pairs found")
            
            for par in pares[:50]:
                if aplicar_filtros(par):
                    pares_validos.append(par)
        except Exception as e:
            print(f"  ⚠️ Error {rede}: {e}")
    
    return pares_validos, total_brutos

def classificar_oportunidade(num_canais):
    if num_canais >= 2:
        return 1, " HIGH CONFIDENCE"
    elif num_canais == 1:
        return 2, " OPPORTUNITY"
    else:
        return 3, "🥉 HIDDEN GEM"

def formatar_alerta(par, nivel, canais_mencionados, ca, token_symbol, chain):
    liq = par.get('liquidity', {}).get('usd', 0)
    pump = par.get('priceChange', {}).get('h1', 0)
    vol = par.get('volume', {}).get('h24', 0)
    mc = par.get('fdv', 0) or par.get('marketCap', 0)
    price = par.get('priceUsd', '0')
    pump_24h = par.get('priceChange', {}).get('h24', 0)
    
    try:
        price_fmt = f"${float(price):.8f}" if price and price != '0' else "N/A"
    except:
        price_fmt = "N/A"
    
    emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
    titulos = {1: "HIGH CONFIDENCE", 2: "OPPORTUNITY", 3: "HIDDEN GEM"}
    descricoes = {
        1: "Multiple alpha channels talking!", 
        2: "One alpha channel spotted it!", 
        3: "Nobody talking yet! Pure alpha!"
    }
    
    dex_link = get_dexscreener_link(ca, chain)
    gmgn_link = get_gmgn_link(ca, chain)
    
    canais_info = ""
    if canais_mencionados:
        canais_info = f"\n📢 *Mentioned:* {', '.join(['@'+c for c in canais_mencionados])}"
    
    msg = (
        f"{emojis[nivel]} *PRIMEAPE 7 - {titulos[nivel]}* {emojis[nivel]}\n\n"
        f"📌 *{descricoes[nivel]}*\n{canais_info}\n\n"
        f"🪙 *Token:* #{token_symbol}\n"
        f"*CA:* `{ca}`\n"
        f"*Chain:* {chain.upper()}\n"
        f"*Price:* {price_fmt}\n"
        f"*Market Cap:* ${mc:,.2f}\n"
        f"*Liquidity:* ${liq:,.2f}\n"
        f"*Vol 24h:* ${vol:,.2f}\n"
        f"*Pump 1h:* {pump}%\n"
        f"*Pump 24h:* {pump_24h}%\n\n"
        f"️ _DYOR!_"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🔍 DexScreener", url=dex_link),
            InlineKeyboardButton("🔄 Update", callback_data="refresh")
        ],
        [InlineKeyboardButton("📊 Analyses", callback_data="show_analyses")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    return msg, reply_markup

async def enviar_status_scan(total_brutos, total_filtrados, total_alertados, total_memoria):
    if total_alertados > 0:
        msg = (
            " *PRIMEAPE 7 - SCAN STATUS*\n\n"
            f"⏰ _{datetime.now().strftime('%H:%M:%S UTC')}_\n\n"
            f"📊 *Statistics:*\n"
            f"• Total pairs scanned: `{total_brutos}`\n"
            f"• Passed filters: `{total_filtrados}`\n"
            f"• 🚨 **New alerts sent: `{total_alertados}`**\n"
            f"• CAs in memory: `{total_memoria}`\n\n"
            f"🌐 *Networks:* SOL | ETH | BSC | BASE\n"
            f" *Channels:* {len(CANAIS_ALPHA)}\n"
        )
        
        keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        enviar_alerta_telegram(msg, reply_markup)

async def main():
    global CANAIS_ALPHA
    
    print("🦍 PrimeApe 7 Started...")
    
    # Carrega os canais automaticamente
    if not CANAIS_ALPHA:
        carregar_canais()
    
    print(f"📡 Monitoring {len(CANAIS_ALPHA)} channels")
    
    # Market Pulse a cada 3h
    if verificar_market_pulse():
        enviar_market_pulse()
    
    cas_enviados = carregar_cas_enviados()
    print(f"📋 {len(cas_enviados)} CAs in memory")
    
    oportunidades, total_brutos = buscar_pares_dexscreener()
    print(f"🎯 {len(oportunidades)} opportunities passed filters!")
    
    novas = [op for op in oportunidades if op.get('pairAddress') not in cas_enviados]
    print(f"✨ {len(novas)} NEW opportunities")
    
    novas.sort(key=lambda x: x.get('liquidity', {}).get('usd', 0) + x.get('volume', {}).get('h24', 0), reverse=True)
    
    total_alertados = 0
    
    if novas:
        novos_cas = []
        for i, op in enumerate(novas[:3], 1):
            token = op.get('baseToken', {}).get('symbol', 'Unknown')
            ca = op.get('pairAddress', 'N/A')
            chain = op.get('chainId', 'Unknown')
            
            print(f"\n[{i}/3] {token} ({chain.upper()})")
            
            num_canais, mencoes = await verificar_canais_telegram(ca)
            nivel, _ = classificar_oportunidade(num_canais)
            
            msg, reply_markup = formatar_alerta(op, nivel, mencoes, ca, token, chain)
            enviar_alerta_telegram(msg, reply_markup)
            
            total_alertados += 1
            novos_cas.append(ca)
            import time
            time.sleep(2)
        
        cas_enviados.extend(novos_cas)
        salvar_cas_enviados(cas_enviados)
        print(f"\n {len(novos_cas)} new CAs saved")
        
        await enviar_status_scan(total_brutos, len(oportunidades), total_alertados, len(cas_enviados))
    else:
        print("\n🔄 No new opportunities - scanning continues...")
    
    commitar_no_github()
    print("\n✅ Done.")

if __name__ == "__main__":
    asyncio.run(main())
