import requests
import os
import asyncio
import json
import base64
import hashlib
from datetime import datetime
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from telethon import TelegramClient
from telethon.sessions import StringSession
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# --- CONFIGURAÇÕES ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_SESSION_STRING = os.getenv('TELEGRAM_SESSION_STRING')
GMGN_API_KEY = os.getenv('GMGN_API_KEY')
GMGN_PRIVATE_KEY = os.getenv('GMGN_PRIVATE_KEY')
PAT_TOKEN = os.getenv('PAT_TOKEN')
REPO_OWNER = os.getenv('REPO_OWNER')
REPO_NAME = os.getenv('REPO_NAME')

CANAIS_ALPHA = []
REDES = ["solana", "ethereum", "bsc", "base"]
SENT_CAS_FILE = "sent_cas.json"
PULSE_CONTROL_FILE = "last_pulse_hour.txt"
MARKET_PULSE_FILE = "last_market_pulse.txt"
CHANNELS_FILE = "channels_list.json"
TELEGRAPH_FILE = "telegraph_config.json"

TOKENS_BLOQUEADOS = [
    'SOL', 'ETH', 'BNB', 'MATIC', 'AVAX', 'FTM', 'ARB', 'OP', 'BASE',
    'NEAR', 'ATOM', 'DOT', 'ADA', 'XRP', 'LTC', 'BCH', 'TRX', 'TON',
    'POL', 'APT', 'SUI', 'SEI', 'TIA', 'JUP', 'RAY', 'ORCA',
    'USDT', 'USDC', 'DAI', 'BUSD', 'USDP', 'TUSD', 'USDD', 'FRAX',
    'PYUSD', 'GUSD', 'FDUSD', 'LUSD', 'SUSD',
    'WETH', 'WSOL', 'WBNB', 'WMATIC', 'WAVAX', 'WFTM', 'WARB', 'WOP',
    'WBTC', 'RENBTC', 'TBTC', 'BTC', 'LINK', 'UNI', 'AAVE', 'SUSHI', 
    'CRV', 'COMP', 'MKR', 'SNX', 'DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 
    'WIF', 'BOME', 'MNGO', 'SRM', 'FTT', 'YFI', 'BAL', 'LDO', 'RPL', 
    'CBETH', 'STETH', 'RETH', 'MYRO', 'POPCAT', 'MOG', 'TURBO', 'MILADY',
    'BSC', 'POL', 'ARB', 'OP', 'MATIC', 'AVAX', 'FTM', 'NEAR', 'ATOM'
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
    global CANAIS_ALPHA
    if os.path.exists(CHANNELS_FILE):
        try:
            with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
                canais = json.load(f)
            CANAIS_ALPHA = [c['identificador'] for c in canais]
            print(f"📋 {len(CANAIS_ALPHA)} canais carregados do arquivo")
            return CANAIS_ALPHA
        except Exception as e:
            print(f"⚠️ Erro ao carregar canais: {e}")
            return []
    else:
        print("⚠️ Arquivo channels_list.json não encontrado")
        return []

def carregar_telegraph_config():
    if os.path.exists(TELEGRAPH_FILE):
        try:
            with open(TELEGRAPH_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def salvar_telegraph_config(config):
    with open(TELEGRAPH_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def criar_ou_atualizar_telegraph(tokens_list):
    config = carregar_telegraph_config()
    content_html = []
    content_html.append({"tag": "p", "children": [f"🦍 PrimeApe 7 Radar - Last scan: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"]})
    content_html.append({"tag": "p", "children": [f"📊 Total gems found: {len(tokens_list)}"]})
    content_html.append({"tag": "hr"})
    
    for i, token in enumerate(tokens_list, 1):
        symbol = token.get('symbol', 'Unknown')
        chain = token.get('chain', 'Unknown').upper()
        ca = token.get('ca', 'N/A')
        mc = token.get('mc', 0)
        liq = token.get('liq', 0)
        vol = token.get('vol', 0)
        pump = token.get('pump_24h', 0)
        channels = token.get('channels', [])
        
        rede_map = {'solana': 'sol', 'ethereum': 'eth', 'bsc': 'bsc', 'base': 'base'}
        rede_short = rede_map.get(chain.lower(), 'sol')
        gmgn_link = f"https://gmgn.ai/{rede_short}/token/{ca}"
        dex_link = f"https://dexscreener.com/{chain.lower()}/{ca}"
        
        content_html.append({"tag": "h3", "children": [f"{i}. @{symbol} - {chain}"]})
        content_html.append({"tag": "p", "children": [f"CA: {ca}"]})
        content_html.append({"tag": "p", "children": [f"MC: ${mc:,.0f} | Liq: ${liq:,.0f} | Vol: ${vol:,.0f} | 24h: {pump:+.1f}%"]})
        content_html.append({"tag": "p", "children": ["Links: ", {"tag": "a", "attrs": {"href": gmgn_link}, "children": ["GMGN"]}, " | ", {"tag": "a", "attrs": {"href": dex_link}, "children": ["DexScreener"]}]})
        
        if channels:
            canais_str = ", ".join([f"@{c}" for c in channels])
            content_html.append({"tag": "p", "children": [f"📢 Mentioned in: {canais_str}"]})
        content_html.append({"tag": "hr"})
    
    content_html.append({"tag": "p", "children": ["_Powered by PrimeApe 7 _"]})
    title = f"PrimeApe 7 - Verified Tokens ({datetime.now().strftime('%d/%m %H:%M')})"
    
    if config and config.get('access_token') and config.get('path'):
        try:
            url = "https://api.telegra.ph/editPage"
            data = {'access_token': config['access_token'], 'path': config['path'], 'title': title, 'content': json.dumps(content_html), 'return_content': 'false'}
            resp = requests.post(url, data=data, timeout=10)
            result = resp.json()
            if result.get('ok'):
                page_url = f"https://telegra.ph{config['path']}"
                print(f"✅ Telegraph page updated: {page_url}")
                return page_url
            else:
                return criar_nova_telegraph(title, content_html)
        except Exception as e:
            print(f"❌ Error: {e}")
            return criar_nova_telegraph(title, content_html)
    else:
        return criar_nova_telegraph(title, content_html)

def criar_nova_telegraph(title, content_html):
    try:
        config = carregar_telegraph_config() or {}
        if not config.get('access_token'):
            url = "https://api.telegra.ph/createAccount"
            data = {'short_name': 'PrimeApe7Bot', 'author_name': 'PrimeApe 7', 'author_url': 'https://t.me/PrimeApe7Bot'}
            resp = requests.post(url, data=data, timeout=10)
            result = resp.json()
            if result.get('ok'):
                config['access_token'] = result['result']['access_token']
                print("✅ Telegraph account created")
            else:
                return None
        
        url = "https://api.telegra.ph/createPage"
        data = {'access_token': config['access_token'], 'title': title, 'content': json.dumps(content_html), 'return_content': 'false'}
        resp = requests.post(url, data=data, timeout=10)
        result = resp.json()
        
        if result.get('ok'):
            path = result['result']['path']
            config['path'] = path
            salvar_telegraph_config(config)
            page_url = f"https://telegra.ph{path}"
            print(f"✅ Telegraph page created: {page_url}")
            return page_url
        else:
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def commitar_no_github():
    if not all([PAT_TOKEN, REPO_OWNER, REPO_NAME]):
        return
    for arquivo in [SENT_CAS_FILE, PULSE_CONTROL_FILE, MARKET_PULSE_FILE, TELEGRAPH_FILE]:
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
        except:
            pass

# --- MARKET PULSE ---
def get_preco_global():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,binancecoin&vs_currencies=usd&include_24hr_change=true"
        resp = requests.get(url, timeout=10).json()
        return {'BTC': resp['bitcoin'], 'ETH': resp['ethereum'], 'SOL': resp['solana'], 'BNB': resp['binancecoin']}
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
            msg += f"*{k}:* ${v['usd']:,.2f} ({change:+.1f}%)\n"
    msg += "\n📡 *Radar Status:*\n"
    msg += "• Scanning: SOL, ETH, BSC, BASE\n"
    msg += f"• Active Channels: {len(CANAIS_ALPHA)}\n"
    msg += "• Only PURE GEMS (no consolidated tokens)\n"
    msg += "\n _Turn on notifications!_"
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
        print("⚠️ Session string not configured")
        return 0, []
    
    canais_que_mencionaram = []
    try:
        client = TelegramClient(StringSession(TELEGRAM_SESSION_STRING), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            print("⚠️ Session invalid")
            return 0, []
        
        print(f"🔍 Scanning {len(CANAIS_ALPHA)} channels for CA...")
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
    data = {"chat_id": TELEGRAM_CHANNEL_ID, "text": mensagem, "parse_mode": parse_mode, "disable_web_page_preview": True}
    if reply_markup:
        data["reply_markup"] = reply_markup.to_json()
    try:
        resp = requests.post(url, json=data, timeout=10)
        if resp.status_code == 200:
            print("✅ Alert sent!")
    except Exception as e:
        print(f" Error: {e}")

def get_gmgn_link(ca, rede):
    rede_map = {'solana': 'sol', 'ethereum': 'eth', 'bsc': 'bsc', 'base': 'base'}
    rede_short = rede_map.get(rede.lower(), 'sol')
    return f"https://gmgn.ai/{rede_short}/token/{ca}"

def get_dexscreener_link(ca, rede):
    return f"https://dexscreener.com/{rede.lower()}/{ca}"

def criar_assinatura_gmgn(method, path, timestamp):
    """Cria assinatura RSA para API GMGN"""
    if not GMGN_PRIVATE_KEY:
        return ""
    
    try:
        # Monta a mensagem a ser assinada
        message = f"{method}{path}{timestamp}"
        
        # Importa a chave privada
        private_key = RSA.import_key(GMGN_PRIVATE_KEY)
        
        # Cria hash SHA256
        h = SHA256.new(message.encode('utf-8'))
        
        # Assina com RSA-PKCS1v15
        signer = pkcs1_15.new(private_key)
        signature = signer.sign(h)
        
        # Retorna em base64
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        print(f"⚠️ Erro ao criar assinatura GMGN: {e}")
        return ""

def aplicar_filtros(par):
    """Retorna (True, None) se passar, ou (False, 'Motivo') se falhar"""
    liq = par.get('liquidity', {}).get('usd', 0)
    mc = par.get('fdv', 0) or par.get('marketCap', 0)
    vol = par.get('volume', {}).get('h24', 0)
    pump_1h = par.get('priceChange', {}).get('h1', 0)
    pump_24h = par.get('priceChange', {}).get('h24', 0)
    
    base_token = par.get('baseToken', {})
    symbol = base_token.get('symbol', '').upper()
    
    if symbol in TOKENS_BLOQUEADOS:
        return False, f"Token bloqueado ({symbol})"
    
    if vol < 500:
        return False, f"Volume muito baixo (${vol:,.0f})"
    
    if pump_24h < 0 or pump_24h > 300:
        return False, f"Pump 24h fora da faixa ({pump_24h}%)"
    
    if pump_1h < -50:
        return False, f"Caindo muito na 1h ({pump_1h}%)"
    
    if mc and mc > 0:
        if vol / mc < 0.01 or vol / mc > 5.0:
            return False, f"Ratio Vol/MC estranho ({vol/mc:.2f})"
    
    pair_address = par.get('pairAddress', '')
    if not pair_address or len(pair_address) < 10:
        return False, "Endereço inválido"
    
    pair_created_at = par.get('pairCreatedAt', 0)
    if pair_created_at:
        created_timestamp = pair_created_at / 1000
        now_timestamp = datetime.now().timestamp()
        age_hours = (now_timestamp - created_timestamp) / 3600
        if age_hours > 48:
            return False, f"Muito antigo ({age_hours:.1f}h)"
    else:
        return False, "Sem data de criação"
    
    return True, None

def buscar_pares_dexscreener():
    print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Scanning DexScreener...")
    pares_validos = []
    total_brutos = 0
    motivos_filtro = {}
    
    tokens_para_busca = {
        "solana": ["USDC", "USDT"],
        "ethereum": ["USDC", "USDT", "DAI"],
        "bsc": ["USDT", "BUSD", "USDC"],
        "base": ["USDC", "USDbC"]
    }
    
    for rede, tokens_base in tokens_para_busca.items():
        for token in tokens_base:
            try:
                url = f"https://api.dexscreener.com/latest/dex/search?q={token}%20{rede}"
                data = requests.get(url, timeout=10).json()
                pares = data.get('pairs', [])
                
                print(f"  🔍 {rede.upper()} ({token}): {len(pares)} raw pairs found")
                total_brutos += len(pares)
                
                for par in pares[:50]:
                    passou, motivo = aplicar_filtros(par)
                    if passou:
                        if par not in pares_validos:
                            pares_validos.append(par)
                    else:
                        motivos_filtro[motivo] = motivos_filtro.get(motivo, 0) + 1
                    
            except Exception as e:
                print(f"  ⚠️ Error {rede} ({token}): {e}")
    
    return pares_validos, total_brutos, motivos_filtro

def buscar_tokens_gmgn():
    """Busca tokens recém-lançados via GMGN.AI Trenches com autenticação RSA"""
    print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Scanning GMGN.AI...")
    tokens_validos = []
    total_brutos = 0
    motivos_filtro = {}
    
    if not GMGN_API_KEY or not GMGN_PRIVATE_KEY:
        print("  ⚠️ GMGN credentials not configured")
        return tokens_validos, total_brutos, motivos_filtro
    
    redes_gmgn = {
        'solana': 'sol',
        'ethereum': 'eth',
        'bsc': 'bsc',
        'base': 'base'
    }
    
    for rede, chain_short in redes_gmgn.items():
        try:
            path = f"/defi/quotation/v1/trenches/{chain_short}"
            timestamp = str(int(datetime.now().timestamp()))
            signature = criar_assinatura_gmgn("GET", path, timestamp)
            
            url = f"https://gmgn.ai{path}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'X-API-Key': GMGN_API_KEY,
                'X-Timestamp': timestamp,
                'X-Signature': signature,
                'Accept': 'application/json'
            }
            
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                tokens = data.get('data', {}).get('trenches', [])
                
                print(f"  ✅ GMGN {chain_short.upper()}: {len(tokens)} tokens found")
                total_brutos += len(tokens)
                
                for token in tokens[:50]:
                    par = {
                        'baseToken': {
                            'symbol': token.get('symbol', ''),
                            'address': token.get('address', '')
                        },
                        'pairAddress': token.get('address', ''),
                        'chainId': rede,
                        'priceUsd': str(token.get('price', 0)),
                        'liquidity': {'usd': token.get('liquidity', 0)},
                        'volume': {'h24': token.get('volume_24h', 0)},
                        'priceChange': {
                            'h1': token.get('price_change_1h', 0),
                            'h24': token.get('price_change_24h', 0)
                        },
                        'fdv': token.get('market_cap', 0),
                        'marketCap': token.get('market_cap', 0),
                        'pairCreatedAt': token.get('created_at', 0)
                    }
                    
                    passou, motivo = aplicar_filtros(par)
                    if passou:
                        if par not in tokens_validos:
                            tokens_validos.append(par)
                    else:
                        motivos_filtro[motivo] = motivos_filtro.get(motivo, 0) + 1
            else:
                print(f"  ⚠️ GMGN {chain_short}: HTTP {resp.status_code}")
                
        except Exception as e:
            print(f"  ⚠️ Error GMGN {chain_short}: {e}")
    
    return tokens_validos, total_brutos, motivos_filtro

def classificar_oportunidade(num_canais):
    if num_canais >= 2:
        return 1, "🥇 HIGH CONFIDENCE"
    elif num_canais == 1:
        return 2, "🥈 OPPORTUNITY"
    else:
        return 3, "🥉 HIDDEN GEM"

def formatar_alerta(par, nivel, canais_mencionados, ca, token_symbol, chain, analyses_url):
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
    
    emojis = {1: "", 2: "🥈", 3: "🥉"}
    titulos = {1: "HIGH CONFIDENCE", 2: "OPPORTUNITY", 3: "HIDDEN GEM"}
    descricoes = {1: "Multiple alpha channels talking!", 2: "One alpha channel spotted it!", 3: "Nobody talking yet! Pure alpha!"}
    
    dex_link = get_dexscreener_link(ca, chain)
    canais_info = f"\n📢 *Mentioned:* {', '.join(['@'+c for c in canais_mencionados])}" if canais_mencionados else ""
    
    msg = (f"{emojis[nivel]} *PRIMEAPE 7 - {titulos[nivel]}* {emojis[nivel]}\n\n"
           f"📌 *{descricoes[nivel]}*\n{canais_info}\n\n"
           f"🪙 *Token:* #{token_symbol}\n*CA:* `{ca}`\n*Chain:* {chain.upper()}\n"
           f"*Price:* {price_fmt}\n*Market Cap:* ${mc:,.2f}\n*Liquidity:* ${liq:,.2f}\n"
           f"*Vol 24h:* ${vol:,.2f}\n*Pump 1h:* {pump}%\n*Pump 24h:* {pump_24h}%\n\n⚠️ _DYOR!_")
    
    keyboard = [[InlineKeyboardButton(" DexScreener", url=dex_link), InlineKeyboardButton("🔄 Update", callback_data="refresh")],
                [InlineKeyboardButton("📊 Analyses", url=analyses_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return msg, reply_markup

async def enviar_status_scan(total_brutos, total_filtrados, total_alertados, total_memoria):
    if total_alertados > 0:
        msg = (f"🦍 *PRIMEAPE 7 - SCAN STATUS*\n\n _{datetime.now().strftime('%H:%M:%S UTC')}_\n\n"
               f"📊 *Statistics:*\n• Total pairs scanned: `{total_brutos}`\n• Passed filters: `{total_filtrados}`\n"
               f"• 🚨 **New alerts sent: `{total_alertados}`**\n• CAs in memory: `{total_memoria}`\n\n"
               f"🌐 *Networks:* SOL | ETH | BSC | BASE\n📡 *Channels:* {len(CANAIS_ALPHA)}\n")
        keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh")]]
        enviar_alerta_telegram(msg, InlineKeyboardMarkup(keyboard))

async def main():
    global CANAIS_ALPHA
    print(" PrimeApe 7 Started...")
    if not CANAIS_ALPHA:
        carregar_canais()
    print(f"📡 Monitoring {len(CANAIS_ALPHA)} channels")
    
    if verificar_market_pulse():
        enviar_market_pulse()
    
    cas_enviados = carregar_cas_enviados()
    print(f"📋 {len(cas_enviados)} CAs in memory")
    
    # Busca DexScreener
    oportunidades_dex, total_dex, motivos_dex = buscar_pares_dexscreener()
    print(f"🎯 DexScreener: {len(oportunidades_dex)} opportunities passed filters!")
    
    # Busca GMGN (COM AUTENTICAÇÃO RSA)
    oportunidades_gmgn, total_gmgn, motivos_gmgn = buscar_tokens_gmgn()
    print(f"🎯 GMGN: {len(oportunidades_gmgn)} opportunities passed filters!")
    
    # Une os resultados
    oportunidades = oportunidades_dex + oportunidades_gmgn
    total_brutos = total_dex + total_gmgn
    
    # Merge dos motivos de filtro para debug
    motivos_filtro = {}
    for motivo, qtd in motivos_dex.items():
        motivos_filtro[motivo] = motivos_filtro.get(motivo, 0) + qtd
    for motivo, qtd in motivos_gmgn.items():
        motivos_filtro[motivo] = motivos_filtro.get(motivo, 0) + qtd
    
    # Imprime relatório de debug
    if motivos_filtro:
        print("\n📊 DEBUG - Motivos de rejeição dos tokens:")
        for motivo, qtd in sorted(motivos_filtro.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  ❌ {motivo}: {qtd} tokens barrados")
        print("-" * 40)
    
    # Remove duplicatas baseado no pairAddress
    seen = set()
    oportunidades_unicas = []
    for op in oportunidades:
        addr = op.get('pairAddress', '')
        if addr and addr not in seen:
            seen.add(addr)
            oportunidades_unicas.append(op)
    
    print(f"🎯 Total unique opportunities: {len(oportunidades_unicas)}")
    
    novas = [op for op in oportunidades_unicas if op.get('pairAddress') not in cas_enviados]
    print(f"✨ {len(novas)} NEW opportunities")
    
    novas.sort(key=lambda x: x.get('liquidity', {}).get('usd', 0) + x.get('volume', {}).get('h24', 0), reverse=True)
    tokens_para_telegraph = []
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
            
            tokens_para_telegraph.append({'symbol': token, 'chain': chain, 'ca': ca, 'mc': op.get('fdv', 0) or op.get('marketCap', 0) or 0,
                                          'liq': op.get('liquidity', {}).get('usd', 0) or 0, 'vol': op.get('volume', {}).get('h24', 0) or 0,
                                          'pump_24h': op.get('priceChange', {}).get('h24', 0) or 0, 'channels': mencoes})
            
            analyses_url = criar_ou_atualizar_telegraph(tokens_para_telegraph)
            if not analyses_url:
                analyses_url = "https://telegra.ph"
            
            msg, reply_markup = formatar_alerta(op, nivel, mencoes, ca, token, chain, analyses_url)
            enviar_alerta_telegram(msg, reply_markup)
            
            total_alertados += 1
            novos_cas.append(ca)
            import time
            time.sleep(2)
        
        cas_enviados.extend(novos_cas)
        salvar_cas_enviados(cas_enviados)
        print(f"\n💾 {len(novos_cas)} new CAs saved")
        await enviar_status_scan(total_brutos, len(oportunidades_unicas), total_alertados, len(cas_enviados))
    else:
        print("\n🔄 No new opportunities - scanning continues...")
    
    commitar_no_github()
    print("\n✅ Done.")

if __name__ == "__main__":
    asyncio.run(main())
