from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models import model_main as mm
from database.db import SessionLocal
from models.db_models import Product
import numpy as np
from numpy.linalg import norm
from openai import AsyncOpenAI
import json, asyncio
from datetime import datetime
import os

# -------------------------------------------------
with open("prompt.json", "r", encoding="utf-8") as f:
    prompt = json.load(f)

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

        if client_id not in chat_log:
            chat_log[client_id] = {"messages": {}}

        messages = chat_log[client_id]["messages"]
        next_idx = str(max(map(int, messages.keys()), default=-1) + 1)

        # --- Kullanıcı mesajını ekle
        messages[next_idx] = {
            "role": "user",
            "content": req_msg,
            "timestamp": datetime.now().isoformat()
        }

        # --- Mesaj tipi
        msg_type = await mm.get_ai_response(
            req_msg, prompt=prompt["selection"]["product"]["tr"]
        )

        # --- Ürün isteği ise
        if msg_type == "ürün_isteği":
            if len(req_msg.split()) <= 3:
                req_msg = f"{req_msg} ürünü almak istiyorum"

            resp = await client.embeddings.create(
                model="text-embedding-3-small",
                input=req_msg
            )
            user_vec = np.array(resp.data[0].embedding, dtype=np.float32)

            best, best_score = None, -1.0
            with SessionLocal() as db:
                for p in db.query(Product).filter(Product.embedding.isnot(None)):
                    prod_vec = np.frombuffer(p.embedding, dtype=np.float32)
                    sim = cosine(user_vec, prod_vec)
                    if sim > best_score:
                        best, best_score = p, sim

            if best:
                bot_reply = f"Size en uygun ürün: {best.name}\nİncelemek için: {best.permalink}"
            else:
                bot_reply = "Üzgünüm, benzer bir ürün bulamadım."

        # --- Normal cevap
        else:
            all_msgs = chat_log[client_id]["messages"]
            sorted_keys = sorted(map(int, all_msgs.keys()))
            recent_msgs = sorted_keys[-10:]  # son 10 mesaj, yoksa olan kadar

            history_text = ""
            for key in recent_msgs:
                m = all_msgs[str(key)]
                who = "Kullanıcı" if m["role"] == "user" else "Bot"
                history_text += f"{who}: {m['content']}\n"

            prompt_text = prompt["caht"]["connect"]["tr"].replace("{}", history_text.strip())

            bot_reply = await mm.get_ai_response(
                req_msg, prompt=prompt_text
            )

        # --- Bot mesajını ekle
        messages[str(int(next_idx) + 1)] = {
            "role": "bot",
            "content": bot_reply,
            "timestamp": datetime.now().isoformat()
        }

        # --- Güncel logu kaydet
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(chat_log, f, ensure_ascii=False, indent=2)

        return {"reply": bot_reply}

    except Exception as e:
        print("❌ chat_handler hatası:", e)
        raise HTTPException(status_code=500, detail=str(e))
