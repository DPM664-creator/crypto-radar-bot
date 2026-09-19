import requests
import os
import asyncio
import json
import base64
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession

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
# LISTA MESTRA DE CANAIS ALPHA (EXPANDIDA GLOBALMENTE)
# ==============================================================================
CANAIS_ALPHA = [
    # --- ORIGINAIS (Base) ---
    'mad_apes_gambles', 'TheDonsCalls', 'TheSolitairePrestige',
    'gubbinscalls', 'mad_apes', 'sadcatgamble',
    'ghastlygems', 'uranusX100', 'ramcalls',
    
    # --- NOVOS APROVADOS (Alpha Curado) ---
    'gogetacalls', 'dylansdegens', 'TWOSICCsPICCs', 'marcellcooks',
    
    # --- SOLICITADOS POR VOCÊ (Degen/Gems) ---
    'Gemsminechat', 'MineGems', 'Degen_Dynasty', 'tigers_callz',
    
    # --- RÚSSIA / CIS (Alta Frequência) ---
    'FRI_Russian_Insiders', 'btctradingclub', 'CRYPTO_insidderr',
    
    # --- COREIA / ÁSIA (Early Tech) ---
    'WeCryptoTogether', 'BSC_SWITZERLAND',
    
    # --- INTERNACIONAL / MEMECOIN ALPHA ---
    'GemHunter', 'ad_crypto', 'Official_GCR', 'OlimpioAlpha',
    'CryptoInnerCircle', 'BinanceKillers', 'WallStreetQueen',
    
    # --- EM OBSERVAÇÃO (Manter por enquanto, avaliar depois) ---
    'roobbiee', 'ancientkols', 'ThanosGems', 'BullishCallsPremium', 'dr_crypto_channel'
]

REDES = ["solana", "ethereum", "bsc", "base"]
SENT_CAS_FILE = "sent_cas.json"
PULSE_CONTROL_FILE = "last_pulse_hour.txt"
ANALYSES_FILE = "analyses.md"

# URL DO RELATÓRIO NO GITHUB
GITHUB_REPORT_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/blob/main/{ANALYSES_FILE}"

# TOKENS NATIVOS E STABLECOINS QUE DEVEM SER IGNORADOS
TOKENS_NATIVOS = [
    'SOL', 'ETH', 'BNB', 'MATIC', 'AVAX', 'FTM', 'ARB', 'OP', 'BASE',
    'USDC', 'USDT', 'DAI', 'WETH', 'WSOL', 'WBNB', 'WBTC'
]

# --- FUNÇÕES DE MEMÓRIA ---
def carregar_cas_enviados():
    if os.path.exists(SENT_CAS_FILE):
        try:
            with open(SENT_CAS_FILE, 'r') as f:
                data = json.load(f)
                return data.get('cas_enviados', [])
        except:
            return []
    return []

def salvar_cas_enviados(cas_enviados):
    with open(SENT_CAS_FILE, 'w') as f:
        json.dump({'cas_enviados': cas_enviados}, f, indent=2)

def commitar_no_github():
    if not all([PAT_TOKEN, REPO_OWNER, REPO_NAME]):
        print("⚠️ GitHub tokens not configured")
        return
    
    for arquivo in [SENT_CAS_FILE, PULSE_CONTROL_FILE, ANALYSES_FILE]:
        if not os.path.exists(arquivo):
            continue
        try:
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
            print(f"✅ {arquivo} saved to GitHub!")
        except Exception as e:
            print(f"❌ Error saving {arquivo}: {e}")

# --- FUNÇÕES DO MARKET PULSE ---
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

def get_top_movers():
    movers = []
    for rede in REDES:
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={rede}"
            pares = requests.get(url, timeout=10).json().get('pairs', [])
            for p in pares[:50]:
                liq = p.get('liquidity', {}).get('usd', 0)
                pump = p.get('priceChange', {}).get('h24', 0)
                vol = p.get('volume', {}).get('h24', 0)
                base = p.get('baseToken', {}).get('symbol', '').upper()
                if base in TOKENS_NATIVOS:
                    continue
                if 20 < pump < 100 and liq > 10000 and vol > 50000:
                    movers.append({
                        'symbol': base,
                        'chain': p.get('chainId', '?').upper(),
                        'pump': pump, 'liq': liq
                    })
        except:
            continue
    
    movers.sort(key=lambda x: x['pump'], reverse=True)
    return movers[:3]

def enviar_market_pulse():
    print(" Sending Market Pulse...")
    precos = get_preco_global()
    movers = get_top_movers()
    
    msg = "🦍 *PRIMEAPE 7 - MARKET PULSE*\n\n"
    
    if precos:
        msg += "📊 *Global Market:*\n"
        for k, v in [('BTC', precos['BTC']), ('ETH', precos['ETH']), ('SOL', precos['SOL']), ('BNB', precos['BNB'])]:
            change = v.get('usd_24h_change', 0)
            emoji = "🟢" if change >= 0 else "🔴"
            msg += f"{emoji} *{k}:* ${v['usd']:,.2f} ({change:+.1f}%)\n"
        msg += "\n"
    
    if movers:
        msg += "🔥 *Top Healthy Movers (24h):*\n"
        for i, m in enumerate(movers, 1):
            msg += f"{i}. *{m['symbol']}* ({m['chain']}) +{m['pump']:.0f}% | Liq: ${m['liq']:,.0f}\n"
        msg += "\n"
    
    msg += "📡 *Radar Status:*\n"
    msg += "• Scanning: SOL, ETH, BSC, BASE\n"
    msg += "• Filters: MC $500-$5M | Liq $500-$500k | Vol $100+ | <7 days\n"
    msg += "• Next alpha scan in 15 min...\n\n"
    msg += "🔔 _Turn on notifications!_"
    
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
        print("⚠️ Session string not configured")
        return 0, []
    
    canais_que_mencionaram = []
    try:
        client = TelegramClient(StringSession(TELEGRAM_SESSION_STRING), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print("⚠️ Session invalid")
            return 0, []
        
        for canal in CANAIS_ALPHA:
            try:
                async for message in client.iter_messages(canal, limit=30):
                    if ca_address.lower() in message.text.lower():
                        if canal not in canais_que_mencionaram:
                            canais_que_mencionaram.append(canal)
                        break
            except Exception as e:
                continue
        
        await client.disconnect()
    except Exception as e:
        print(f"❌ Telegram connection error: {e}")
    
    return len(canais_que_mencionaram), canais_que_mencionaram

def enviar_alerta_telegram(mensagem, reply_markup=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHANNEL_ID, 
        "text": mensagem, 
        "parse_mode": "Markdown", 
        "disable_web_page_preview": False
    }
    if reply_markup:
        data["reply_markup"] = reply_markup.to_json()
    
    try:
        resp = requests.post(url, json=data, timeout=10)
        if resp.status_code == 200:
            print("✅ Alert with buttons sent!")
        else:
            print(f"❌ Error: {resp.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

def get_gmgn_link(ca, rede):
    """Gera link GMGN baseado na rede"""
    rede_map = {
        'solana': 'sol',
        'ethereum': 'eth',
        'bsc': 'bsc',
        'base': 'base'
    }
    rede_short = rede_map.get(rede.lower(), 'sol')
    return f"https://gmgn.ai/{rede_short}/token/{ca}"

def gerar_analyses_file(token_data_list):
    """Gera arquivo de análises com todos os CAs verificados"""
    content = "# 🦍 PRIMEAPE 7 - VERIFIED TOKENS ANALYSIS\n\n"
    content += f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    content += f"**Total Tokens Tracked:** {len(token_data_list)}\n\n"
    content += "---\n\n"
    
    for i, token in enumerate(token_data_list, 1):
        ca = token.get('ca', 'N/A')
        symbol = token.get('symbol', 'Unknown')
        rede = token.get('chain', 'Unknown')
        canais = token.get('channels', [])
        mc = token.get('mc', 0)
        liq = token.get('liq', 0)
        vol = token.get('vol', 0)
        pump = token.get('pump_24h', 0)
        
        gmgn_link = get_gmgn_link(ca, rede)
        dex_link = f"https://dexscreener.com/{rede.lower()}/{ca}"
        
        content += f"## {i}. **{symbol}** ({rede.upper()})\n\n"
        content += f"**CA:** `{ca}`\n"
        content += f"**Market Cap:** ${mc:,.2f}\n"
        content += f"**Liquidity:** ${liq:,.2f}\n"
        content += f"**Volume 24h:** ${vol:,.2f}\n"
        content += f"**Pump 24h:** {pump:+.1f}%\n\n"
        
        content += "**📊 Analysis Links:**\n"
        content += f"- [GMGN Analysis]({gmgn_link})\n"
        content += f"- [DexScreener]({dex_link})\n\n"
        
        if canais:
            content += "**📢 Mentioned In:**\n"
            for canal in canais:
                canal_link = f"https://t.me/{canal}"
                content += f"- [@{canal}]({canal_link})\n"
        
        content += "\n---\n\n"
    
    with open(ANALYSES_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"📊 Analyses file saved: {ANALYSES_FILE}")

def aplicar_filtros(par):
    """Filtros RELAXADOS para capturar tokens dos canais"""
    
    # Dados básicos
    liq = par.get('liquidity', {}).get('usd', 0)
    mc = par.get('fdv', 0) or par.get('marketCap', 0)
    vol = par.get('volume', {}).get('h24', 0)
    pump_1h = par.get('priceChange', {}).get('h1', 0)
    pump_24h = par.get('priceChange', {}).get('h24', 0)
    
    # Token info
    base_token = par.get('baseToken', {})
    symbol = base_token.get('symbol', '').upper()
    
    # ❌ FILTRAR TOKENS NATIVOS E STABLECOINS
    if symbol in TOKENS_NATIVOS:
        return False
    
    # ✅ MARKET CAP: $500 - $5M
    if not mc or mc < 500 or mc > 5000000:
        return False
    
    # ✅ LIQUIDEZ: $500 - $500k
    if not liq or liq < 500 or liq > 500000:
        return False
    
    # ✅ VOLUME: Mínimo $100
    if vol < 100:
        return False
    
    # ✅ PUMP 24h: 0% - 500%
    if pump_24h < 0 or pump_24h > 500:
        return False
    
    # ✅ PUMP 1h: Não pode estar caindo mais de 50%
    if pump_1h < -50:
        return False
    
    # ✅ RAZÃO VOLUME/MC: 0.01 - 5.0
    if vol / mc < 0.01 or vol / mc > 5.0:
        return False
    
    # ✅ PAR DE NEGOCIAÇÃO: Deve ter endereço válido
    pair_address = par.get('pairAddress', '')
    if not pair_address or len(pair_address) < 10:
        return False
    
    # ⚠️ FILTRO DE IDADE: Token criado há menos de 7 DIAS
    pair_created_at = par.get('pairCreatedAt', 0)
    if pair_created_at:
        created_timestamp = pair_created_at / 1000
        now_timestamp = datetime.now().timestamp()
        age_days = (now_timestamp - created_timestamp) / 86400
        
        if age_days > 7:
            return False
    else:
        pass
    
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
        return 2, " OPPORTUNITY"
    else:
        return 3, "🥉 HIDDEN GEM"

def formatar_alerta_com_botoes(par, nivel, canais_mencionados, ca, token_symbol, chain):
    """Formata alerta COM 3 BOTÕES: DexScreener | Update | Analyses"""
    
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
    
    dex_link = f"https://dexscreener.com/{chain.lower()}/{ca}"
    gmgn_link = get_gmgn_link(ca, chain)
    
    canais_info = ""
    if canais_mencionados:
        canais_info = f"\n📢 *Mentioned:* {', '.join(['@'+c for c in canais_mencionados])}"
    
    msg = (
        f"{emojis[nivel]} *PRIMEAPE 7 - {titulos[nivel]}* {emojis[nivel]}\n\n"
        f"📌 *{descricoes[nivel]}*\n{canais_info}\n\n"
        f"🪙 *Token:* #{token_symbol} ({token_symbol})\n"
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
    
    # Cria os 3 botões
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [
            InlineKeyboardButton("🔍 DexScreener", url=dex_link),
            InlineKeyboardButton("🔄 Update", callback_data="refresh")
        ],
        [InlineKeyboardButton("📊 Analyses", url=GITHUB_REPORT_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    return msg, reply_markup

async def main():
    print("🦍 PrimeApe 7 Started...")
    
    # 1. Market Pulse (if it's time)
    if verificar_pulse_horario():
        enviar_market_pulse()
    
    # 2. Scan Opportunities
    cas_enviados = carregar_cas_enviados()
    print(f"📋 {len(cas_enviados)} CAs in memory")
    
    oportunidades = buscar_pares_dexscreener()
    print(f"🎯 {len(oportunidades)} opportunities passed filters!")
    
    novas = [op for op in oportunidades if op.get('pairAddress') not in cas_enviados]
    print(f"✨ {len(novas)} NEW opportunities")
    
    novas.sort(key=lambda x: x.get('liquidity', {}).get('usd', 0) + x.get('volume', {}).get('h24', 0), reverse=True)
    
    # Lista para armazenar dados das análises
    token_data_list = []
    
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
            msg, reply_markup = formatar_alerta_com_botoes(op, nivel, mencoes, ca, token, chain)
            enviar_alerta_telegram(msg, reply_markup)
            
            # Adiciona dados para o arquivo de análises
            token_data = {
                'ca': ca,
                'symbol': token,
                'chain': chain,
                'channels': mencoes,
                'mc': op.get('fdv', 0) or op.get('marketCap', 0) or 0,
                'liq': op.get('liquidity', {}).get('usd', 0) or 0,
                'vol': op.get('volume', {}).get('h24', 0) or 0,
                'pump_24h': op.get('priceChange', {}).get('h24', 0) or 0
            }
            token_data_list.append(token_data)
            
            novos_cas.append(ca)
            import time
            time.sleep(2)
        
        # Atualiza arquivo de análises
        if token_data_list:
            # Carrega dados antigos se existirem
            if os.path.exists(ANALYSES_FILE):
                try:
                    with open(ANALYSES_FILE, 'r') as f:
                        # Parse simples para extrair CAs existentes
                        content = f.read()
                        # Mantém os últimos 20 tokens
                        token_data_list = token_data_list[-20:]
                except:
                    pass
            
            gerar_analyses_file(token_data_list)
        
        cas_enviados.extend(novos_cas)
        salvar_cas_enviados(cas_enviados)
        print(f"\n💾 {len(novos_cas)} new CAs saved")
    else:
        print("\n🔄 No new opportunities")
        
    commitar_no_github()
    print("\n✅ Done.")

if __name__ == "__main__":
    asyncio.run(main())
