"""
Crypto Radar Bot - Fase 1: Monitoramento Real
Monitora contas do X em busca de novos Contract Addresses (CA)
Usa ntscraper (sem necessidade de login)
"""

from ntscraper import Nitter
import re
import os

# Lista das contas para monitorar
CONTAS_ALVO = [
    "MEADGod",
    "A1lon9", 
    "Tier10k"
]

# Padrão para encontrar Contract Addresses (0x... com 40 caracteres)
CA_PATTERN = re.compile(r'\b0x[a-fA-F0-9]{40}\b')

def main():
    print("🚀 Crypto Radar Bot iniciado...")
    print(f"📡 Monitorando {len(CONTAS_ALVO)} contas do X...\n")
    
    # Criar scraper
    scraper = Nitter(log_level=1)
    
    for conta in CONTAS_ALVO:
        print(f"🔍 Buscando tweets recentes de @{conta}...")
        
        try:
            # Buscar tweets recentes (modo simples, sem login)
            tweets = scraper.get_tweets(conta, mode='user', number=5)
            
            if tweets and 'tweets' in tweets:
                lista_tweets = tweets['tweets']
                print(f"   ✅ Encontrados {len(lista_tweets)} tweets recentes\n")
                
                for tweet in lista_tweets:
                    texto = tweet.get('text', '')
                    
                    # Procurar por Contract Addresses
                    cas_encontrados = CA_PATTERN.findall(texto)
                    
                    if cas_encontrados:
                        print(f"   🎯 CA ENCONTRADO!")
                        print(f"   Texto: {texto[:150]}...")
                        for ca in cas_encontrados:
                            print(f"   💎 Contract Address: {ca}")
                        print()
            else:
                print(f"   ⚠️ Nenhum tweet encontrado\n")
                
        except Exception as e:
            print(f"   ❌ Erro ao buscar tweets de @{conta}: {e}\n")
    
    print("✅ Monitoramento concluído!")

if __name__ == "__main__":
    main()
