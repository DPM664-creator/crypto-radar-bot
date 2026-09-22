import asyncio
import json
import os
import requests
import base64
from telethon import TelegramClient
from telethon.sessions import StringSession

async def main():
    API_ID = os.getenv('TELEGRAM_API_ID')
    API_HASH = os.getenv('TELEGRAM_API_HASH')
    SESSION_STRING = os.getenv('TELEGRAM_SESSION_STRING')
    PAT_TOKEN = os.getenv('PAT_TOKEN')
    REPO_OWNER = os.getenv('REPO_OWNER')
    REPO_NAME = os.getenv('REPO_NAME')
    
    if not all([API_ID, API_HASH, SESSION_STRING]):
        print("❌ Credenciais Telegram não configuradas")
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
    
    # Salva a lista localmente
    with open('channels_list.json', 'w', encoding='utf-8') as f:
        json.dump(canais, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎯 Total extraído: {len(canais)} grupos/canais")
    print("💾 Lista salva localmente")
    
    # Faz commit via API do GitHub
    if all([PAT_TOKEN, REPO_OWNER, REPO_NAME]):
        print("\n Enviando para o GitHub via API...")
        try:
            with open('channels_list.json', 'r', encoding='utf-8') as f:
                content = f.read()
            content_b64 = base64.b64encode(content.encode()).decode()
            
            url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/channels_list.json"
            headers = {
                'Authorization': f'token {PAT_TOKEN}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Verifica se o arquivo já existe
            response = requests.get(url, headers=headers)
            sha = None
            if response.status_code == 200:
                sha = response.json()['sha']
                print("  📝 Arquivo existente, atualizando...")
            
            # Cria ou atualiza o arquivo
            data = {
                'message': '📋 Lista de canais extraída automaticamente',
                'content': content_b64
            }
            if sha:
                data['sha'] = sha
            
            response = requests.put(url, headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                print("✅ Arquivo enviado com sucesso para o GitHub!")
            else:
                print(f"❌ Erro ao enviar: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"❌ Erro: {e}")
    else:
        print("⚠️ Credenciais do GitHub não configuradas, arquivo salvo apenas localmente")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
