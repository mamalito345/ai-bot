from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models import model_main as mm
import numpy as np
from numpy.linalg import norm
from openai import AsyncOpenAI
import json, asyncio
from datetime import datetime
import os

# -------------------------------------------------

LOG_FILE = "chat_log.json"

# İlk başta dosya yoksa oluştur
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

router = APIRouter()
client = AsyncOpenAI()

class ChatRequest(BaseModel):
    message: str
    client_id: str

class ChatResponse(BaseModel):
    reply: str

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (norm(a) * norm(b)))

# -------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
async def chat_handler(payload: ChatRequest):
    try:
        req_msg   = payload.message.strip()
        client_id = payload.client_id.strip()

        # --- Log dosyasını oku
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            chat_log = json.load(f)

        # Kullanıcı ilk defa geliyorsa sadece messages alanı oluştur
        if client_id not in chat_log:
            chat_log[client_id] = { "messages": {} }

        messages = chat_log[client_id]["messages"]
        next_idx = str(max(map(int, messages.keys()), default=-1) + 1)

        # --- Kullanıcı mesajını ekle
        messages[next_idx] = {
            "role": "user",
            "content": req_msg,
            "timestamp": datetime.now().isoformat()
        }

        # En fazla 50 mesaj sakla
        all_keys = sorted(map(int, messages.keys()))
        if len(all_keys) > 50:
            to_delete = all_keys[:len(all_keys) - 50]
            for k in to_delete:
                del messages[str(k)]

        # Geçmişin son 10 mesajını topla
        sorted_keys = sorted(map(int, messages.keys()))
        last_keys = sorted_keys[-10:]

        history_text = ""
        for key in last_keys:
            m = messages[str(key)]
            who = "Kullanıcı" if m["role"] == "user" else "Bot"
            history_text += f"{who}: {m['content']}\n"

        # Tüm geçmiş + son kullanıcı mesajı
        full_prompt = history_text.strip() + f"\nMesaj Geçmişi: {req_msg}"

        # AI çağrısı (sadece cevap al)
        bot_reply = await mm.get_ai_response(user_message=full_prompt)

        # --- Bot yanıtını ekle
        next_idx = str(max(map(int, messages.keys()), default=-1) + 1)
        messages[next_idx] = {
            "role": "bot",
            "content": bot_reply,
            "timestamp": datetime.now().isoformat()
        }

        # Kaydet
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(chat_log, f, ensure_ascii=False, indent=2)

        return ChatResponse(reply=bot_reply)

    except Exception as e:
        import traceback
        print("❌ chat_handler hatası:")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Sunucuda beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyin."
        )

