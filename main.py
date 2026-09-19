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

# ==============================================================================
# LISTA MESTRA DE CANAIS ALPHA
# ==============================================================================
CANAIS_ALPHA = [
    'mad_apes_gambles', 'TheDonsCalls', 'TheSolitairePrestige',
    'gubbinscalls', 'mad_apes', 'sadcatgamble',
    'ghastlygems', 'uranusX100', 'ramcalls',
    'gogetacalls', 'dylansdegens', 'TWOSICCsPICCs', 'marcellcooks',
    'Gemsminechat', 'MineGems', 'Degen_Dynasty', 'tigers_callz',
    'FRI_Russian_Insiders', 'btctradingclub', 'CRYPTO_insidderr',
    'WeCryptoTogether', 'BSC_SWITZERLAND',
    'GemHunter', 'ad_crypto', 'Official_GCR', 'OlimpioAlpha',
    'CryptoInnerCircle', 'BinanceKillers', 'WallStreetQueen',
    'roobbiee', 'ancientkols', 'ThanosGems', 'BullishCallsPremium', 'dr_crypto_channel'
]

REDES = ["solana", "ethereum", "bsc", "base"]
SENT_CAS_FILE = "sent_cas.json"
PULSE_CONTROL_FILE = "last_pulse_hour.txt"

TOKENS_NATIVOS = [
    'SOL', 'ETH', 'BNB', 'MATIC', 'AVAX', 'FTM', 'ARB', 'OP', 'BASE',
    'USDC', 'USDT', 'DAI', 'WETH', 'WSOL', 'WBNB', 'WBTC'
]

# Lista global para armazenar tokens verificados (não alertados)
TOKENS_VERIFICADOS = []

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

def commitar_no_github():
    if not all([PAT_TOKEN, REPO_OWNER, REPO_NAME]):
        return
    
    for arquivo in [SENT_CAS_FILE, PULSE_CONTROL_FILE]:
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

# --- MARKET PULSE ---
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
    print("📡 Sending Market Pulse...")
    precos = get_preco_global()
    
    msg = "🦍 *PRIMEAPE 7 - MARKET PULSE*\n\n"
    
    if precos:
        msg += "📊 *Global Market:*\n"
        for k, v in [('BTC', precos['BTC']), ('ETH', precos['ETH']), ('SOL', precos['SOL']), ('BNB', precos['BNB'])]:
            change = v.get('usd_24h_change', 0)
            emoji = "🟢" if change >= 0 else "🔴"
            msg += f"{emoji} *{k}:* ${v['usd']:,.2f} ({change:+.1f}%)\n"
    
    msg += "\n📡 *Radar Status:*\n"
    msg += "• Scanning: SOL, ETH, BSC, BASE\n"
    msg += "• Filters: MC $500-$5M | Liq $500-$500k | <7 days\n"
    msg += "\n🔔 _Turn on notifications!_"
    
    enviar_alerta_telegram(msg)

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
        return 0, []
    
    canais_que_mencionaram = []
    try:
        client = TelegramClient(StringSession(TELEGRAM_SESSION_STRING), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            return 0, []
        
        for canal in CANAIS_ALPHA:
            try:
                async for message in client.iter_messages(canal, limit=30):
                    if ca_address.lower() in message.text.lower():
                        if canal not in canais_que_mencionaram:
                            canais_que_mencionaram.append(canal)
                        break
            except:
                continue
        
        await client.disconnect()
    except:
        pass
    
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
    
    if not mc or mc < 500 or mc > 5000000:
        return False
    
    if not liq or liq < 500 or liq > 500000:
        return False
    
    if vol < 100:
        return False
    
    if pump_24h < 0 or pump_24h > 500:
        return False
    
    if pump_1h < -50:
        return False
    
    if vol / mc < 0.01 or vol / mc > 5.0:
        return False
    
    pair_address = par.get('pairAddress', '')
    if not pair_address or len(pair_address) < 10:
        return False
    
    pair_created_at = par.get('pairCreatedAt', 0)
    if pair_created_at:
        created_timestamp = pair_created_at / 1000
        now_timestamp = datetime.now().timestamp()
        age_days = (now_timestamp - created_timestamp) / 86400
        
        if age_days > 7:
            return False
    
    return True

def buscar_pares_dexscreener():
    print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Scanning pairs...")
    pares_validos = []
    
    for rede in REDES:
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={rede}"
            data = requests.get(url, timeout=10).json()
            pares = data.get('pairs', [])
            print(f"  🔍 {rede.upper()}: {len(pares)} raw pairs found")
            
            for par in pares[:50]:
                if aplicar_filtros(par):
                    pares_validos.append(par)
        except Exception as e:
            print(f"  ⚠️ Error {rede}: {e}")
    
    return pares_validos

def classificar_oportunidade(num_canais):
    if num_canais >= 2:
        return 1, "🥇 HIGH CONFIDENCE"
    elif num_canais == 1:
        return 2, "🥈 OPPORTUNITY"
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
        f"⚠️ _DYOR!_"
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

def formatar_analyses_token(token_data, motivo_filtro):
    """Formata um token para o relatório de análises"""
    symbol = token_data.get('symbol', 'Unknown')
    chain = token_data.get('chain', 'Unknown')
    ca = token_data.get('ca', 'N/A')
    
    gmgn_link = get_gmgn_link(ca, chain)
    dex_link = get_dexscreener_link(ca, chain)
    
    msg = (
        f"🪙 **@{symbol}** - {chain.upper()}\n"
        f"`{ca}`\n"
        f"[🔍 GMGN]({gmgn_link}) | [📈 DexScreener]({dex_link})\n"
        f"⚠️ _{motivo_filtro}_"
    )
    
    return msg

async def enviar_analyses_completo():
    """Envia o relatório completo de tokens verificados (não alertados)"""
    global TOKENS_VERIFICADOS
    
    if not TOKENS_VERIFICADOS:
        msg = "📊 **ANALYSES REPORT**\n\n_No tokens verified yet._"
        enviar_alerta_telegram(msg, parse_mode="Markdown")
        return
    
    msg = "📊 **PRIMEAPE 7 - VERIFIED TOKENS**\n\n"
    msg += f"_Total: {len(TOKENS_VERIFICADOS)} tokens_\n\n"
    msg += "=" * 40 + "\n\n"
    
    for i, token in enumerate(TOKENS_VERIFICADOS[-10:], 1):  # Últimos 10 tokens
        motivo = token.get('filter_reason', 'Filtered by criteria')
        msg += f"**{i}.** {formatar_analyses_token(token, motivo)}\n\n"
    
    msg += "=" * 40
    msg += "\n\n_Updated: " + datetime.now().strftime('%H:%M:%S UTC') + "_"
    
    # Botão para atualizar
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh_analyses")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    enviar_alerta_telegram(msg, reply_markup, parse_mode="Markdown")

async def main():
    global TOKENS_VERIFICADOS
    
    print("🦍 PrimeApe 7 Started...")
    
    if verificar_pulse_horario():
        enviar_market_pulse()
    
    cas_enviados = carregar_cas_enviados()
    print(f"📋 {len(cas_enviados)} CAs in memory")
    
    oportunidades = buscar_pares_dexscreener()
    print(f"🎯 {len(oportunidades)} opportunities passed filters!")
    
    novas = [op for op in oportunidades if op.get('pairAddress') not in cas_enviados]
    print(f"✨ {len(novas)} NEW opportunities")
    
    novas.sort(key=lambda x: x.get('liquidity', {}).get('usd', 0) + x.get('volume', {}).get('h24', 0), reverse=True)
    
    if novas:
        novos_cas = []
        for i, op in enumerate(novas[:3], 1):
            token = op.get('baseToken', {}).get('symbol', 'Unknown')
            ca = op.get('pairAddress', 'N/A')
            chain = op.get('chainId', 'Unknown')
            
            print(f"\n[{i}/3] {token} ({chain.upper()})")
            
            num_canais, mencoes = await verificar_canais_telegram(ca)
            nivel, _ = classificar_oportunidade(num_canais)
            
            # Envia alerta COM BOTÕES
            msg, reply_markup = formatar_alerta(op, nivel, mencoes, ca, token, chain)
            enviar_alerta_telegram(msg, reply_markup)
            
            novos_cas.append(ca)
            import time
            time.sleep(2)
        
        cas_enviados.extend(novos_cas)
        salvar_cas_enviados(cas_enviados)
        print(f"\n💾 {len(novos_cas)} new CAs saved")
    else:
        print("\n🔄 No new opportunities to alert")
    
    # Verifica tokens que passaram filtros básicos mas não foram alertados
    # (aqui você pode adicionar lógica adicional se necessário)
    
    commitar_no_github()
    print("\n✅ Done.")

if __name__ == "__main__":
    asyncio.run(main())
