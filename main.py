import requests
import os
from datetime import datetime

# --- CONFIGURAÇÃO ---
# Redes que vamos monitorar na DexScreener
REDES = ["solana", "ethereum", "bsc"]

def buscar_pares_dexscreener():
    print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] Buscando novos pares na DexScreener...")
    pares_validos = []
    
    # Busca os pares mais recentes de cada rede
    for rede in REDES:
        try:
            # Endpoint da DexScreener para pares recentes
            url = f"https://api.dexscreener.com/latest/dex/tokens/{rede}" 
            # Nota: Para simplificar, estamos buscando tokens gerais. 
            # Em produção, usaríamos o endpoint de 'pairs' ordenado por criação.
            url_search = f"https://api.dexscreener.com/latest/dex/search?q={rede}"
            
            response = requests.get(url_search, timeout=10)
            data = response.json()
            pares = data.get('pairs', [])
            
            # Filtrar apenas pares criados recentemente (ex: última hora)
            # DexScreener não dá data exata de criação no search, então pegamos os top 50 de cada rede
            for par in pares[:50]: 
                if aplicar_filtros_iniciais(par):
                    pares_validos.append(par)
                    
        except Exception as e:
            print(f"  ⚠️ Erro ao buscar {rede}: {e}")
            
    return pares_validos

def aplicar_filtros_iniciais(par):
    """Aplica os 3 primeiros filtros do Peneirão"""
    
    # Filtro 1: Liquidez < $1k -> Descartado
    liquidez = par.get('liquidity', {}).get('usd', 0)
    if not liquidez or liquidez < 1000:
        return False
        
    # Filtro 2: Volume > 10% do Market Cap -> Descartado (Wash Trading)
    volume_24h = par.get('volume', {}).get('h24', 0)
    market_cap = par.get('fdv', 0) or par.get('marketCap', 0)
    
    if market_cap and market_cap > 0:
        ratio = volume_24h / market_cap
        if ratio > 0.10: # 10%
            return False
            
    # Filtro 3: Pump > 5% em 1h -> Descartado (Chegou tarde)
    pump_1h = par.get('priceChange', {}).get('h1', 0)
    if pump_1h > 5.0:
        return False
        
    return True

def main():
    print("🚀 Crypto Radar Bot Iniciado (Modo Custo Zero)...")
    
    # 1. Buscar e Filtrar
    oportunidades = buscar_pares_dexscreener()
    
    print(f"\n🎯 {len(oportunidades)} Oportunidades Validadas (Filtros 1, 2 e 3):")
    print("-" * 50)
    
    for op in oportunidades[:5]: # Mostra apenas as top 5 para não poluir o log
        print(f" Par: {op.get('baseToken', {}).get('symbol')} / {op.get('quoteToken', {}).get('symbol')}")
        print(f"   CA: {op.get('pairAddress')}")
        print(f"   Rede: {op.get('chainId')}")
        print(f"   Liquidez: ${op.get('liquidity', {}).get('usd', 0):,.2f}")
        print(f"   Pump 1h: {op.get('priceChange', {}).get('h1', 0)}%")
        print("-" * 50)

    print("✅ Fim da execução.")

if __name__ == "__main__":
    main()
