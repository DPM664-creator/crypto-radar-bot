import asyncio
import json
import os
from telethon import TelegramClient
from telethon.sessions import StringSession

async def main():
    API_ID = os.getenv('TELEGRAM_API_ID')
    API_HASH = os.getenv('TELEGRAM_API_HASH')
    SESSION_STRING = os.getenv('TELEGRAM_SESSION_STRING')
    
    if not all([API_ID, API_HASH, SESSION_STRING]):
        print("❌ Credenciais não configuradas")
        return
    
    print("🦍 Conectando na sua conta Telegram...")
    
    client = TelegramClient(StringSession(SESSION_STRING), int(API_ID), API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ Session inválida - precisa gerar nova")
        return
    
    print("✅ Conectado! Extraindo grupos/canais...\n")
    
    canais = []
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        
        # Pega apenas grupos e canais (ignora conversas privadas)
        if hasattr(entity, 'title'):
            titulo = entity.title
            username = entity.username if hasattr(entity, 'username') and entity.username else None
            eh_canal = hasattr(entity, 'broadcast') and entity.broadcast
            tipo = "canal" if eh_canal else "grupo"
            membros = entity.participants_count if hasattr(entity, 'participants_count') else 0
            
            # Usa @username se existir, senão usa o título exato
            identificador = f"@{username}" if username else titulo
            
            canais.append({
                'titulo': titulo,
                'username': username,
                'identificador': identificador,
                'tipo': tipo,
                'membros': membros
            })
            
            print(f"  ✅ {titulo} ({tipo} - {membros} membros)")
    
    # Salva a lista
    with open('channels_list.json', 'w', encoding='utf-8') as f:
        json.dump(canais, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎯 Total extraído: {len(canais)} grupos/canais")
    print("💾 Lista salva em: channels_list.json")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
