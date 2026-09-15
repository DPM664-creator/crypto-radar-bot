"""
Crypto Radar Bot - Fase 1: Monitoramento Real
Monitora 38 contas do X em busca de novos Contract Addresses (CA)
"""

from twikit import Client
import asyncio
import os
import re

# Lista das contas para monitorar (vamos expandir para 38 depois)
CONTAS_ALVO = [
    "MEADGod",
    "A1lon9", 
    "Tier10k"
]

# Padrão para encontrar Contract Addresses (formato 0x...)
CA_PATTERN = re.compile(r'\b0x[a-fA-F0-9]{40}\b')

async def main():
    print("🚀 Crypto Radar Bot iniciado...")
    
    # Pegar credenciais dos secrets do GitHub
    username = os.getenv('TWITTER_USERNAME')
    password = os.getenv('TWITTER_PASSWORD')
    email = os.getenv('TWITTER_EMAIL')
    
    if not all([username, password, email]):
        print("❌ Erro: Credenciais não configuradas!")
        return
    
    try:
        # Criar cliente e fazer login
        client = Client()
        
        print("🔑 Fazendo login no X...")
        await client.login(
            auth_info_1=username,
            auth_info_2=password,
            password=password
        )
        print("✅ Login realizado com sucesso!")
        
        # Monitorar cada conta
        for conta in CONTAS_ALVO:
            print(f"\n📡 Buscando tweets de @{conta}...")
            
            try:
                # Buscar tweets recentes da conta
                user = await client.get_user_by_screen_name(conta)
                tweets = await user.get_tweets(count=5)  # Últimos 5 tweets
                
                print(f"  Encontrados {len(tweets)} tweets recentes")
                
                # Analisar cada tweet
                for tweet in tweets:
                    texto = tweet.text
                    
                    # Procurar por Contract Addresses
                    cas_encontrados = CA_PATTERN.findall(texto)
                    
                    if cas_encontrados:
                        print(f"\n  🎯 CA ENCONTRADO no tweet: {tweet.id}")
                        print(f"  Texto: {texto[:100]}...")
                        for ca in cas_encontrados:
                            print(f"  💎 Contract Address: {ca}")
                            # Aqui vamos adicionar os filtros depois
                            
            except Exception as e:
                print(f"  ⚠️ Erro ao buscar tweets de @{conta}: {e}")
        
        print("\n✅ Monitoramento concluído!")
        
    except Exception as e:
        print(f"❌ Erro fatal: {e}")

if __name__ == "__main__":
    asyncio.run(main())
