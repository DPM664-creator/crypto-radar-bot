import requests
import os
import asyncio
from datetime import datetime
from telethon import TelegramClient

# --- CONFIGURAÇÕES ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')

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
    
    return len(canais_que_mencionaram), canais_que_mencionados

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
        print(f" Erro: {e}")

def buscar_pares_dexscreener():
    print(f" [{datetime.now().strftime('%H:%M:%S')}] Buscando pares...")
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
    # Filtro 1: Liquidez mínima $5k
    liquidez = par.get('liquidity', {}).get('usd', 0)
    if not liquidez or liquidez < 5000:
        return False
    
    # Filtro 2: Market Cap mínimo $10k (NOVO)
    market_cap = par.get('fdv', 0) or par.get('marketCap', 0)
    if not market_cap or market_cap < 10000:
        return False
    
    # Filtro 3: Volume < 10% do MC (wash trading)
    volume_24h = par.get('volume', {}).get('h24', 0)
    if volume_24h > 0:
        ratio = volume_24h / market_cap
        if ratio > 0.10:
            return False
    
    # Filtro 4: Pump máximo 10% em 1h (era 5%)
    pump_1h = par.get('priceChange', {}).get('h1', 0)
    if pump_1h > 10.0:
        return False
    
    # Filtro 5: Volume mínimo $1k (evita pares muito novos)
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
    
    emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
    titulos = {1: "HIGH CONFIDENCE", 2: "OPPORTUNITY", 3: "HIDDEN GEM"}
    descricoes = {
        1: "Multiple alpha channels talking!",
        2: "One alpha channel spotted it!",
        3: "Nobody talking yet! Pure alpha!"
    }
    
    dex_link = f"https://dexscreener.com/{rede.lower()}/{ca}"
    
    canais_info = ""
    if canais_mencionados:
        canais_info = f"\n📢 *Mentioned:* {', '.join(['@'+c for c in canais_mencionados])}"
    
    mensagem = f"""{emojis[nivel]} *PRIMEAPE 7 - {titulos[nivel]}* {emojis[nivel]}

{descricoes[nivel]}
{canais_info}

 {dex_link}

🥇 *Token:* #{token_symbol} ({token_symbol})
*CA:* `{ca}`
*Chain:* {rede}
*Price:* {price_formatted}
*Market Cap:* ${market_cap:,.2f}
*Liquidity:* ${liquidez:,.2f}
*Vol 24h:* ${volume_24h:,.2f}
*Pump 1h:* {pump_1h}%

✅ *Filters:*
• Liquidity > $5k
• Market Cap > $10k
• Volume OK
• Pump < 10%
• Pair age > 1h

️ _DYOR!_"""

    return mensagem

async def main():
    print(" PrimeApe 7 Iniciado...")
    
    oportunidades = buscar_pares_dexscreener()
    print(f"\n🎯 {len(oportunidades)} oportunidades!")
    
    # Ordenar por qualidade
    oportunidades.sort(key=lambda x: x.get('liquidity', {}).get('usd', 0) + x.get('volume', {}).get('h24', 0), reverse=True)
    
    if oportunidades:
        for i, op in enumerate(oportunidades[:3], 1):
            token = op.get('baseToken', {}).get('symbol', 'Unknown')
            ca = op.get('pairAddress', 'N/A')
            
            print(f"\n[{i}/3] {token}")
            
            num_canais, canais_mencionados = await verificar_canais_telegram(ca)
            nivel, _ = classificar_oportunidade(num_canais)
            
            mensagem = formatar_alerta(op, nivel, canais_mencionados)
            enviar_alerta_telegram(mensagem)
            
            import time
            time.sleep(2)
    else:
        enviar_alerta_telegram("*PrimeApe 7*\n\n No opportunities found.\n\n_Radar active!_")

    print("\n✅ Fim.")

if __name__ == "__main__":
    asyncio.run(main())
