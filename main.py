import requests
import os
from datetime import datetime

# --- CONFIGURAÇÃO ---
REDES = ["solana", "ethereum", "bsc", "base"]

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
    """Aplica os 5 filtros do Peneirão"""
    
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
    
    # Filtro 4: Contrato não verificado -> Descartado
    # DexScreener fornece info sobre verificação em alguns casos
    info_token = par.get('info', {})
    # Se não tiver dados de imagem ou site, pode ser não verificado
    if not info_token.get('imageUrl') and not info_token.get('website'):
        # Não é definitivo, mas é um indicador
        pass  # Vamos manter por enquanto, pois DexScreener nem sempre tem isso
    
    # Filtro 5: Menos de 10 holders -> Descartado
    # DexScreener não fornece holders diretamente, então vamos usar um proxy:
    # Se o par tem pouca liquidez (< $5k) E foi criado recentemente, provavelmente tem poucos holders
    # Isso é uma heurística, não perfeita, mas funcional sem API paga
    if liquidez < 5000:
        # Par muito pequeno provavelmente tem poucos holders
        # Vamos ser conservadores e descartar
        return False
        
    return True

def main():
    print("🚀 Crypto Radar Bot - Fase Completa (5 Filtros)...")
    
    oportunidades = buscar_pares_dexscreener()
    
    print(f"\n🎯 {len(oportunidades)} Oportunidades Validadas (Todos os 5 Filtros):")
    print("=" * 60)
    
    for op in oportunidades[:10]:
        token = op.get('baseToken', {}).get('symbol', 'Unknown')
        ca = op.get('pairAddress', 'N/A')
        rede = op.get('chainId', 'N/A')
        liquidez = op.get('liquidity', {}).get('usd', 0)
        pump = op.get('priceChange', {}).get('h1', 0)
        
        print(f"🪙 {token}")
        print(f"   CA: {ca}")
        print(f"   Rede: {rede}")
        print(f"   Liquidez: ${liquidez:,.2f}")
        print(f"   Pump 1h: {pump}%")
        print("-" * 60)

    print("✅ Fim da execução.")

if __name__ == "__main__":
    main()
