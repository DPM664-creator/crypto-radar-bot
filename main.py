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
    
    # --- NOVOS APROVados (Alpha Curado) ---
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
DEBUG_REPORT_FILE = "debug_report.html"

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
        print("️ Tokens do GitHub não configurados")
        return
    
    for arquivo in [SENT_CAS_FILE, PULSE_CONTROL_FILE, DEBUG_REPORT_FILE]:
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
        msg += " *Global Market:*\n"
        for k, v in [('BTC', precos['BTC']), ('ETH', precos['ETH']), ('SOL', precos['SOL']), ('BNB', precos['BNB'])]:
            change = v.get('usd_24h_change', 0)
            emoji = "🟢" if change >= 0 else "🔴"
            msg += f"{emoji} *{k}:* ${v['usd']:,.2f} ({change:+.1f}%)\n"
        msg += "\n"
    
    if movers:
        msg += " *Top Healthy Movers (24h):*\n"
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
                async for message in client.iter_messages(canal, limit=30):
                    if ca_address.lower() in message.text.lower():
                        if canal not in canais_que_mencionaram:
                            canais_que_mencionaram.append(canal)
                        break
            except Exception as e:
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

def analisar_par(par, rede):
    """Analisa um par e retorna dict com dados + motivo do filtro"""
    liq = par.get('liquidity', {}).get('usd', 0) or 0
    mc = par.get('fdv', 0) or par.get('marketCap', 0) or 0
    vol = par.get('volume', {}).get('h24', 0) or 0
    pump_1h = par.get('priceChange', {}).get('h1', 0) or 0
    pump_24h = par.get('priceChange', {}).get('h24', 0) or 0
    
    base_token = par.get('baseToken', {})
    symbol = base_token.get('symbol', 'N/A')
    ca = par.get('pairAddress', 'N/A')
    price = par.get('priceUsd', '0')
    
    motivos = []
    if symbol.upper() in TOKENS_NATIVOS:
        motivos.append("TOKEN NATIVO")
    if mc < 2000 or mc > 500000:
        motivos.append(f"MC fora (${mc:,.0f})")
    if liq < 1000 or liq > 100000:
        motivos.append(f"Liq fora (${liq:,.0f})")
    if vol < 1000:
        motivos.append(f"Vol baixo (${vol:,.0f})")
    if pump_24h < 5 or pump_24h > 200:
        motivos.append(f"Pump 24h {pump_24h:+.1f}%")
    if pump_1h < -20:
        motivos.append(f"Dump 1h {pump_1h:+.1f}%")
    if mc > 0 and vol > 0 and (vol / mc < 0.05 or vol / mc > 2.0):
        motivos.append("Vol/MC desbalanceado")
    
    aprovado = len(motivos) == 0
    
    return {
        'rede': rede.upper(),
        'symbol': symbol,
        'ca': ca,
        'mc': mc,
        'liq': liq,
        'vol': vol,
        'pump_1h': pump_1h,
        'pump_24h': pump_24h,
        'price': price,
        'aprovado': aprovado,
        'motivos': motivos
    }

def aplicar_filtros(par):
    """Filtros RIGOROSOS para encontrar GEMAS REAIS"""
    liq = par.get('liquidity', {}).get('usd', 0)
    mc = par.get('fdv', 0) or par.get('marketCap', 0)
    vol = par.get('volume', {}).get('h24', 0)
    pump_1h = par.get('priceChange', {}).get('h1', 0)
    pump_24h = par.get('priceChange', {}).get('h24', 0)
    
    base_token = par.get('baseToken', {})
    symbol = base_token.get('symbol', '').upper()
    
    if symbol in TOKENS_NATIVOS:
        return False
    if not mc or mc < 2000 or mc > 500000:
        return False
    if not liq or liq < 1000 or liq > 100000:
        return False
    if vol < 1000:
        return False
    if pump_24h < 5 or pump_24h > 200:
        return False
    if pump_1h < -20:
        return False
    if vol / mc < 0.05 or vol / mc > 2.0:
        return False
    pair_address = par.get('pairAddress', '')
    if not pair_address or len(pair_address) < 10:
        return False
    
    return True

def gerar_relatorio_html(analises):
    """Gera um relatório HTML interativo com todos os pares analisados"""
    total = len(analises)
    aprovados = sum(1 for a in analises if a['aprovado'])
    filtrados = total - aprovados
    
    linhas_tabela = ""
    for i, a in enumerate(analises, 1):
        status_class = "aprovado" if a['aprovado'] else "filtrado"
        status_text = "✅ APROVADO" if a['aprovado'] else "❌ FILTRADO"
        motivos_html = "<br>".join(a['motivos']) if a['motivos'] else "-"
        dex_link = f"https://dexscreener.com/{a['rede'].lower()}/{a['ca']}"
        
        # Formatação de valores
        mc_fmt = f"${a['mc']:,.0f}"
        liq_fmt = f"${a['liq']:,.0f}"
        vol_fmt = f"${a['vol']:,.0f}"
        pump_24h_fmt = f"{a['pump_24h']:+.1f}%"
        pump_1h_fmt = f"{a['pump_1h']:+.1f}%"
        
        # Cor do pump
        cor_pump_24h = "green" if a['pump_24h'] > 0 else "red"
        cor_pump_1h = "green" if a['pump_1h'] > 0 else "red"
        
        linhas_tabela += f"""
        <tr class="{status_class}">
            <td>{i}</td>
            <td><b>{a['rede']}</b></td>
            <td><b>{a['symbol']}</b></td>
            <td><a href="{dex_link}" target="_blank" class="ca-link" title="Ver no DexScreener">{a['ca'][:8]}...{a['ca'][-6:]}</a></td>
            <td>{mc_fmt}</td>
            <td>{liq_fmt}</td>
            <td>{vol_fmt}</td>
            <td style="color:{cor_pump_24h}"><b>{pump_24h_fmt}</b></td>
            <td style="color:{cor_pump_1h}"><b>{pump_1h_fmt}</b></td>
            <td><span class="status-badge {status_class}">{status_text}</span></td>
            <td class="motivos">{motivos_html}</td>
        </tr>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>🦍 PrimeApe 7 - Relatório de Varredura</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: 'Segoe UI', Tahoma, sans-serif;
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: #fff;
        padding: 20px;
        min-height: 100vh;
    }}
    .container {{ max-width: 1600px; margin: 0 auto; }}
    h1 {{
        text-align: center;
        font-size: 2.5em;
        margin-bottom: 10px;
        background: linear-gradient(90deg, #f7971e, #ffd200);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .subtitulo {{
        text-align: center;
        color: #aaa;
        margin-bottom: 30px;
        font-size: 1.1em;
    }}
    .stats {{
        display: flex;
        justify-content: center;
        gap: 20px;
        margin-bottom: 30px;
        flex-wrap: wrap;
    }}
    .stat-card {{
        background: rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px 30px;
        text-align: center;
        min-width: 150px;
        border: 1px solid rgba(255,255,255,0.2);
    }}
    .stat-card .numero {{
        font-size: 2.5em;
        font-weight: bold;
    }}
    .stat-card .label {{ color: #aaa; font-size: 0.9em; margin-top: 5px; }}
    .stat-total .numero {{ color: #ffd200; }}
    .stat-aprovado .numero {{ color: #00ff88; }}
    .stat-filtrado .numero {{ color: #ff4444; }}
    
    .tabela-container {{
        overflow-x: auto;
        background: rgba(0,0,0,0.3);
        border-radius: 15px;
        padding: 20px;
        backdrop-filter: blur(10px);
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9em;
    }}
    th {{
        background: rgba(247, 151, 30, 0.3);
        padding: 12px 8px;
        text-align: left;
        border-bottom: 2px solid #f7971e;
        color: #ffd200;
        position: sticky;
        top: 0;
    }}
    td {{
        padding: 10px 8px;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        vertical-align: middle;
    }}
    tr:hover {{ background: rgba(255,255,255,0.05); }}
    tr.aprovado {{ background: rgba(0, 255, 136, 0.08); }}
    tr.filtrado {{ background: rgba(255, 68, 68, 0.05); }}
    
    .ca-link {{
        color: #00d4ff;
        text-decoration: none;
        font-family: monospace;
        font-size: 0.85em;
    }}
    .ca-link:hover {{
        color: #ffd200;
        text-decoration: underline;
    }}
    .status-badge {{
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: bold;
        display: inline-block;
    }}
    .status-badge.aprovado {{
        background: rgba(0, 255, 136, 0.2);
        color: #00ff88;
    }}
    .status-badge.filtrado {{
        background: rgba(255, 68, 68, 0.2);
        color: #ff4444;
    }}
    .motivos {{
        font-size: 0.8em;
        color: #ff8888;
        max-width: 200px;
    }}
    .footer {{
        text-align: center;
        margin-top: 30px;
        color: #666;
        font-size: 0.9em;
    }}
    .filtro-info {{
        background: rgba(255,255,255,0.05);
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        font-size: 0.9em;
    }}
    .filtro-info b {{ color: #ffd200; }}
</style>
</head>
<body>
<div class="container">
    <h1>🦍 PRIMEAPE 7 - RELATÓRIO DE VARREDURA</h1>
    <p class="subtitulo">Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
    
    <div class="stats">
        <div class="stat-card stat-total">
            <div class="numero">{total}</div>
            <div class="label">Total Analisados</div>
        </div>
        <div class="stat-card stat-aprovado">
            <div class="numero">{aprovados}</div>
            <div class="label">✅ Aprovados (Gemas)</div>
        </div>
        <div class="stat-card stat-filtrado">
            <div class="numero">{filtrados}</div>
            <div class="label">❌ Filtrados</div>
        </div>
    </div>
    
    <div class="filtro-info">
        <b>Filtros Ativos:</b> MC $2k-$500k | Liq $1k-$100k | Vol 24h ≥ $1k | Pump 24h 5%-200% | Pump 1h ≥ -20% | Vol/MC 0.05-2.0 | Sem tokens nativos
    </div>
    
    <div class="tabela-container">
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Rede</th>
                    <th>Token</th>
                    <th>CA (DexScreener)</th>
                    <th>Market Cap</th>
                    <th>Liquidez</th>
                    <th>Vol 24h</th>
                    <th>Pump 24h</th>
                    <th>Pump 1h</th>
                    <th>Status</th>
                    <th>Motivo do Filtro</th>
                </tr>
            </thead>
            <tbody>
                {linhas_tabela}
            </tbody>
        </table>
    </div>
    
    <div class="footer">
         PrimeApe 7 • Radar de Gemas • {datetime.now().year}
    </div>
</div>
</body>
</html>"""
    
    with open(DEBUG_REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"📊 Relatório HTML salvo: {DEBUG_REPORT_FILE}")

def buscar_pares_dexscreener():
    print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Buscando pares...")
    pares_validos = []
    todas_analises = []
    
    for rede in REDES:
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={rede}"
            data = requests.get(url, timeout=10).json()
            pares = data.get('pairs', [])
            print(f"  🔍 {rede.upper()}: {len(pares)} pares brutos encontrados")
            
            # Analisa os primeiros 50 pares de cada rede para o relatório
            for par in pares[:50]:
                analise = analisar_par(par, rede)
                todas_analises.append(analise)
                if aplicar_filtros(par):
                    pares_validos.append(par)
        except Exception as e:
            print(f"  ⚠️ Erro {rede}: {e}")
    
    # Gera o relatório HTML com todas as análises
    gerar_relatorio_html(todas_analises)
    
    return pares_validos

def classificar_oportunidade(num_canais):
    if num_canais >= 2:
        return 1, " HIGH CONFIDENCE"
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
    
    emojis = {1: "", 2: "🥈", 3: "🥉"}
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
    
    novas.sort(key=lambda x: x.get('liquidity', {}).get('usd', 0) + x.get('volume', {}).get('h24', 0), reverse=True)
    
    if novas:
        novos_cas = []
        for i, op in enumerate(novas[:3], 1):
            token = op.get('baseToken', {}).get('symbol', 'Unknown')
            ca = op.get('pairAddress', 'N/A')
            print(f"\n[{i}/3] {token} ({op.get('chainId', '?').upper()})")
            
            num_canais, mencoes = await verificar_canais_telegram(ca)
            nivel, _ = classificar_oportunidade(num_canais)
            
            enviar_alerta_telegram(formatar_alerta(op, nivel, mencoes))
            novos_cas.append(ca)
            import time
            time.sleep(2)
        
        cas_enviados.extend(novos_cas)
        salvar_cas_enviados(cas_enviados)
        print(f"\n💾 {len(novos_cas)} novos CAs salvos")
    else:
        print("\n🔄 Nenhuma oportunidade nova")
        
    commitar_no_github()
    print("\n✅ Fim.")

if __name__ == "__main__":
    asyncio.run(main())
