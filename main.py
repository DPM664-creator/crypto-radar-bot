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

# Canais para monitorar (os 9 que você passou)
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
    """Verifica em quantos canais o CA foi mencionado"""
    if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH]):
        print("⚠️ Credenciais API Telegram não configuradas")
        return 0, []
    
    canais_que_mencionaram = []
    
    try:
        client = TelegramClient('primeape_session', TELEGRAM_API_ID, TELEGRAM_API_HASH)
        await client.start()
        
        for canal in CANAIS_ALPHA:
            try:
                # Busca mensagens recentes do canal
                async for message in client.iter_messages(canal, limit=20):
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
    """Envia alerta formatado para o canal PrimeApe 7"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("⚠️ Credenciais do Bot Telegram não configuradas")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            print("✅ Alerta enviado para o canal PrimeApe 7!")
        else:
            print(f"❌ Erro ao enviar: {response.text}")
    except Exception as e:
        print(f"❌ Erro na conexão Telegram: {e}")

def buscar_pares_dexscreener():
    print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Buscando novos pares na DexScreener...")
    pares_validos = []
    
    for rede in REDES:
        try:
            url_search = f"https://api.dexscreener.com/latest/dex/search?q={rede}"
            response = requests.get(url_search, timeout=10)
            data = response.json()
            pares = data.get('pairs', [])
            
            for par in pares[:50]:
                if aplicar_todos_filtros(par):
                    pares_validos.append(par)
                    
        except Exception as e:
            print(f"  ⚠️ Erro ao buscar {rede}: {e}")
            
    return pares_validos

def aplicar_todos_filtros(par):
    """Aplica os 5 filtros do Peneirão PrimeApe"""
    
    # Filtro 1: Liquidez < $1k -> Descartado
    liquidez = par.get('liquidity', {}).get('usd', 0)
    if not liquidez or liquidez < 1000:
        return False
        
    # Filtro 2: Volume > 10% do Market Cap -> Descartado (Wash Trading)
    volume_24h = par.get('volume', {}).get('h24', 0)
    market_cap = par.get('fdv', 0) or par.get('marketCap', 0)
    
    if market_cap and market_cap > 0:
        ratio = volume_24h / market_cap
        if ratio > 0.10:
            return False
            
    # Filtro 3: Pump > 5% em 1h -> Descartado
    pump_1h = par.get('priceChange', {}).get('h1', 0)
    if pump_1h > 5.0:
        return False
    
    # Filtro 4: Contrato verificado (heurística básica)
    info_token = par.get('info', {})
    # Não descartamos só por isso, DexScreener nem sempre tem
    
    # Filtro 5: Liquidez mínima de $5k (proxy para holders)
    if liquidez < 5000:
        return False
        
    return True

def classificar_oportunidade(num_canais):
    """Classifica a oportunidade em níveis"""
    if num_canais >= 2:
        return 1, "🔥 ALTA CONFIANÇA"
    elif num_canais == 1:
        return 2, "💎 OPORTUNIDADE"
    else:
        return 3, "🚀 GEM ESCONDIDA"

def formatar_alerta(par, nivel, canais_mencionados):
    """Formata mensagem bonita para o Telegram"""
    token_symbol = par.get('baseToken', {}).get('symbol', 'Unknown')
    quote_symbol = par.get('quoteToken', {}).get('symbol', 'Unknown')
    ca = par.get('pairAddress', 'N/A')
    rede = par.get('chainId', 'N/A').upper()
    liquidez = par.get('liquidity', {}).get('usd', 0)
    pump_1h = par.get('priceChange', {}).get('h1', 0)
    volume_24h = par.get('volume', {}).get('h24', 0)
    price = par.get('priceUsd', '0')
    
    # Formatar preço corretamente
    try:
        price_formatted = f"${float(price):.8f}" if price and price != '0' else "N/A"
    except:
        price_formatted = "N/A"
    
    # Emoji baseado no nível
    emojis = {1: "🔥", 2: "", 3: "🚀"}
    emoji = emojis.get(nivel, "🦍")
    
    # Link do DexScreener
    dex_link = f"https://dexscreener.com/{rede.lower()}/{ca}"
    
    # Info dos canais
    canais_info = ""
    if canais_mencionados:
        canais_info = f"\n📢 <b>Mencionado em:</b> {', '.join(['@'+c for c in canais_mencionados])}"
    
    # Descrição do nível
    descricoes = {
        1: "<b>ALTA CONFIANÇA</b> - Múltiplos canais estão falando!",
        2: "<b>OPORTUNIDADE</b> - Um canal identificou!",
        3: "<b>GEM ESCONDIDA</b> - Ninguém está falando ainda! Alpha puro!"
    }
    
    mensagem = f"""{emoji} <b>PRIMEAPE 7 - {nivel}º NÍVEL DETECTADO</b> {emoji}

{descricoes[nivel]}
{canais_info}

🪙 <b>Token:</b> {token_symbol}/{quote_symbol}
🔗 <b>CA:</b> <code>{ca}</code>
🌐 <b>Rede:</b> {rede}
💰 <b>Preço:</b> {price_formatted}
 <b>Liquidez:</b> ${liquidez:,.2f}
📊 <b>Volume 24h:</b> ${volume_24h:,.2f}
📈 <b>Pump 1h:</b> {pump_1h}%

✅ <b>Filtros PrimeApe:</b>
• Liquidez > $1k
• Volume OK (sem wash trading)
• Pump aceitável
• Liquidez mínima $5k

🔍 <a href="{dex_link}">Ver no DexScreener</a>

⚠️ <i>Faça sua própria pesquisa (DYOR)!</i>"""

    return mensagem

async def main():
    print(" PrimeApe 7 - Crypto Radar Bot Iniciado...")
    print("=" * 60)
    
    # Buscar e filtrar pares
    oportunidades = buscar_pares_dexscreener()
    
    print(f"\n {len(oportunidades)} oportunidades passaram nos filtros!")
    print("=" * 60)
    
    # Processar cada oportunidade
    if oportunidades:
        for i, op in enumerate(oportunidades[:3], 1):  # Limita a 3 alertas por execução
            token = op.get('baseToken', {}).get('symbol', 'Unknown')
            ca = op.get('pairAddress', 'N/A')
            
            print(f"\n[{i}/{len(oportunidades[:3])}] Verificando: {token}")
            
            # Verificar canais do Telegram
            num_canais, canais_mencionados = await verificar_canais_telegram(ca)
            
            # Classificar
            nivel, classificacao = classificar_oportunidade(num_canais)
            
            print(f"  Nível {nivel} - {classificacao}")
            print(f"  Canais: {len(canais_mencionados)} menções")
            
            # Formatar e enviar
            mensagem = formatar_alerta(op, nivel, canais_mencionados)
            enviar_alerta_telegram(mensagem)
            
            # Pausa entre envios
            import time
            time.sleep(2)
    else:
        print("Nenhuma oportunidade encontrada nesta rodada.")
        enviar_alerta_telegram("<b>PrimeApe 7</b>\n\n🔍 Nenhuma oportunidade validada nos últimos 15 minutos.\n\n<i>O radar continua ativo!</i>")

    print("\n✅ Fim da execução.")

if __name__ == "__main__":
    asyncio.run(main())
