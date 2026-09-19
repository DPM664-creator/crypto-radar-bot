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
                return json.load(f).get('cas_enviados', [])
        except:
            return []
    return []

def salvar_cas_enviados(cas_enviados):
    with open(SENT_CAS_FILE, 'w') as f:
        json.dump({'cas_enviados': cas_enviados}, f, indent=2)

def commitar_no_github():
    if not all([PAT_TOKEN, REPO_OWNER, REPO_NAME]):
        print("⚠️ Tokens do GitHub não configurados")
        return
    
    for arquivo in [SENT_CAS_FILE, PULSE_CONTROL_FILE]:
        if not os.path.exists(arquivo):
            continue
        try:
            with open(arquivo, 'r') as f:
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
            print(f"✅ {arquivo} salvo no GitHub!")
        except Exception as e:
            print(f"❌ Erro ao salvar {arquivo}: {e}")

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
    print("📡 Enviando Market Pulse...")
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
    msg += "• Filters: MC $2k-$500k | Vol $1k+ | Pump 5-200%\n"
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
        print("⚠️ Session string não configurada")
        return 0, []
    
    canais_que_mencionaram = []
    try:
        client = TelegramClient(StringSession(TELEGRAM_SESSION_STRING), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print("⚠️ Session inválida")
            return 0, []
        
        for canal in CANAIS_ALPHA:
            try:
                # Limitado a 30 mensagens para evitar timeout do GitHub Actions e ser mais rápido
                async for message in client.iter_messages(canal, limit=30):
                    if ca_address.lower() in message.text.lower():
                        if canal not in canais_que_mencionaram:
                            canais_que_mencionaram.append(canal)
                        break
            except Exception as e:
                # Ignora canais privados sem acesso ou erros de rate limit
                continue
        
        await client.disconnect()
    except Exception as e:
        print(f"❌ Erro na conexão Telegram: {e}")
    
    return len(canais_que_mencionaram), canais_que_mencionaram

def enviar_alerta_telegram(mensagem):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHANNEL_ID, "text": mensagem, "parse_mode": "Markdown", "disable_web_page_preview": False}
    try:
        resp = requests.post(url, json=data, timeout=10)
        if resp.status_code == 200:
            print("✅ Alerta enviado!")
        else:
            print(f"❌ Erro: {resp.text}")
    except Exception as e:
        print(f"❌ Erro: {e}")

def buscar_pares_dexscreener():
    print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Buscando pares...")
    pares_validos = []
    for rede in REDES:
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={rede}"
            data = requests.get(url, timeout=10).json()
            pares = data.get('pairs', [])
            print(f"  🔍 {rede.upper()}: {len(pares)} pares brutos encontrados")
            for par in pares[:150]: # Aumentado para 150 para pegar mais gems
                if aplicar_filtros(par):
                    pares_validos.append(par)
        except Exception as e:
            print(f"  ⚠️ Erro {rede}: {e}")
    return pares_validos

def aplicar_filtros(par):
    """Filtros RIGOROSOS para encontrar GEMAS REAIS"""
    
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
    
    # ✅ MARKET CAP: Entre $2k e $500k (GEMAS MUITO EARLY!)
    if not mc or mc < 2000 or mc > 500000:
        return False
    
    # ✅ LIQUIDEZ: Mínimo $1k, máximo $100k
    if not liq or liq < 1000 or liq > 100000:
        return False
    
    # ✅ VOLUME: Pelo menos $1k nas últimas 24h
    if vol < 1000:
        return False
    
    # ✅ PUMP 24h: Entre 5% e 200% (movimento real, não estourado)
    if pump_24h < 5 or pump_24h > 200:
        return False
    
    # ✅ PUMP 1h: Não pode estar caindo forte (> -20%)
    if pump_1h < -20:
        return False
    
    # ✅ RAZÃO VOLUME/MC: Entre 0.05 e 2.0 (atividade saudável, sem wash trading absurdo)
    if vol / mc < 0.05 or vol / mc > 2.0:
        return False
    
    # ✅ PAR DE NEGOCIAÇÃO: Deve ter endereço válido
    pair_address = par.get('pairAddress', '')
    if not pair_address or len(pair_address) < 10:
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
    token = par.get('baseToken', {}).get('symbol', 'Unknown')
    ca = par.get('pairAddress', 'N/A')
    rede = par.get('chainId', 'N/A').upper()
    liq = par.get('liquidity', {}).get('usd', 0)
    pump = par.get('priceChange', {}).get('h1', 0)
    vol = par.get('volume', {}).get('h24', 0)
    mc = par.get('fdv', 0) or par.get('marketCap', 0)
    price = par.get('priceUsd', '0')
    
    try:
        price_fmt = f"${float(price):.8f}" if price and price != '0' else "N/A"
    except:
        price_fmt = "N/A"
    
    emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
    titulos = {1: "HIGH CONFIDENCE", 2: "OPPORTUNITY", 3: "HIDDEN GEM"}
    descricoes = {1: "Multiple alpha channels talking!", 2: "One alpha channel spotted it!", 3: "Nobody talking yet! Pure alpha!"}
    
    dex_link = f"[DexScreener](https://dexscreener.com/{rede.lower()}/{ca})"
    
    canais_info = ""
    if canais_mencionados:
        canais_info = f"\n📢 *Mentioned:* {', '.join(['@'+c for c in canais_mencionados])}"
    
    return (
        f"{emojis[nivel]} *PRIMEAPE 7 - {titulos[nivel]}* {emojis[nivel]}\n\n"
        f"📌 *{descricoes[nivel]}*\n{canais_info}\n\n"
        f"🥇 *Token:* #{token} ({token})\n*CA:* `{ca}`\n*Chain:* {rede}\n"
        f"*Price:* {price_fmt}\n*Market Cap:* ${mc:,.2f}\n*Liquidity:* ${liq:,.2f}\n"
        f"*Vol 24h:* ${vol:,.2f}\n*Pump 1h:* {pump}%\n\n"
        f"{dex_link}\n\n⚠️ _DYOR!_"
    )

async def main():
    print("🦍 PrimeApe 7 Iniciado...")
    
    # 1. Market Pulse (se for a hora)
    if verificar_pulse_horario():
        enviar_market_pulse()
    
    # 2. Scan de Oportunidades
    cas_enviados = carregar_cas_enviados()
    print(f"📋 {len(cas_enviados)} CAs na memória")
    
    oportunidades = buscar_pares_dexscreener()
    print(f"🎯 {len(oportunidades)} oportunidades nos filtros!")
    
    novas = [op for op in oportunidades if op.get('pairAddress') not in cas_enviados]
    print(f"✨ {len(novas)} oportunidades NOVAS")
    
    # Ordena por liquidez + volume para priorizar as mais "reais"
    novas.sort(key=lambda x: x.get('liquidity', {}).get('usd', 0) + x.get('volume', {}).get('h24', 0), reverse=True)
    
    if novas:
        novos_cas = []
        # Processa no máximo 3 novas oportunidades por rodada para não estourar o tempo do GitHub
        for i, op in enumerate(novas[:3], 1):
            token = op.get('baseToken', {}).get('symbol', 'Unknown')
            ca = op.get('pairAddress', 'N/A')
            print(f"\n[{i}/3] {token} ({op.get('chainId', '?').upper()})")
            
            num_canais, mencoes = await verificar_canais_telegram(ca)
            nivel, _ = classificar_oportunidade(num_canais)
            
            enviar_alerta_telegram(formatar_alerta(op, nivel, mencoes))
            novos_cas.append(ca)
            import time
            time.sleep(2) # Pausa para evitar rate limit do Telegram
        
        cas_enviados.extend(novos_cas)
        salvar_cas_enviados(cas_enviados)
        print(f"\n💾 {len(novos_cas)} novos CAs salvos")
    else:
        print("\n🔄 Nenhuma oportunidade nova")
        
    commitar_no_github()
    print("\n✅ Fim.")

if __name__ == "__main__":
    asyncio.run(main())
