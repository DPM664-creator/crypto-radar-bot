"""
Crypto Radar Bot - Fase 1: Monitoramento
Monitora 38 contas do X em busca de novos Contract Addresses (CA)
"""

from twikit import Client
import asyncio
import json

# Lista das 38 contas para monitorar (vamos expandir depois)
CONTAS_ALVO = [
    "MEADGod",
    "A1lon9", 
    "Tier10k"
    # Vamos adicionar as outras 35 depois
]

async def main():
    print(" Crypto Radar Bot iniciado...")
    print(f"Monitorando {len(CONTAS_ALVO)} contas do X...")
    
    # Aqui vamos adicionar o código de monitoramento
    # Por enquanto, só um teste básico
    
    for conta in CONTAS_ALVO:
        print(f"📡 Verificando conta: @{conta}")
    
    print("✅ Verificação concluída!")

if __name__ == "__main__":
    asyncio.run(main())
