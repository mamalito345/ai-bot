from fastapi import APIRouter, Request
import asyncio
import aiohttp
import json
import os

router = APIRouter()

YOUR_PHONE_NUMBER_ID = os.getenv("YOUR_PHONE_NUMBER_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def send_whatsapp_message(phone_number, message):
    url = f"https://graph.facebook.com/v17.0/{YOUR_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "text": {"body": message}
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            return await response.json()

async def ask_chatgpt(message):
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 500
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            result = await response.json()
            return result['choices'][0]['message']['content']

async def process_message(sender_phone, message_text):
    try:
        chatgpt_response = await ask_chatgpt(message_text)
        await send_whatsapp_message(sender_phone, chatgpt_response)
    except Exception as e:
        print(f"Hata: {e}")
        await send_whatsapp_message(sender_phone, "Üzgünüm, bir hata oluştu.")

@router.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get('hub.mode')
    token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge
    return {"error": "Forbidden"}

@router.post("/webhook")
async def handle_webhook(request: Request):
    try:
        data = await request.json()
        
        # Debug için yazdır
        print("=== WEBHOOK POST ALINDI ===")
        print(json.dumps(data, indent=2))
        print("==========================")
        
        if 'entry' in data:
            for entry in data['entry']:
                if 'changes' in entry:
                    for change in entry['changes']:
                        print(f"Change field: {change.get('field')}")
                        if 'messages' in change['value']:
                            print("Mesajlar bulundu!")
                            for message in change['value']['messages']:
                                if message['type'] == 'text':
                                    sender_phone = message['from']
                                    message_text = message['text']['body']
                                    
                                    print(f"Mesaj: {message_text}")
                                    print(f"Gönderen: {sender_phone}")
                                    
                                    asyncio.create_task(process_message(sender_phone, message_text))
                                else:
                                    print(f"Mesaj tipi: {message['type']}")
                        else:
                            print("Mesaj bulunamadı, change.value içeriği:")
                            print(json.dumps(change['value'], indent=2))
        else:
            print("Entry bulunamadı")
        
        return {"status": "success"}
    
    except Exception as e:
        print(f"Webhook hatası: {e}")
        return {"status": "error", "message": str(e)}