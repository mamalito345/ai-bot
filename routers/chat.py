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
        
        all_keys = sorted(map(int, messages.keys()))
        if len(all_keys) > 50:
            to_delete = all_keys[:len(all_keys) - 50]
            for k in to_delete:
                del messages[str(k)]

        # --- Mesaj tipi
        msg_type = await mm.get_ai_response(
            req_msg, prompt=prompt["selection"]["product"]["tr"]
        )



        # --- İlgili işlemi yap
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

        elif msg_type == "tasarım_isteği":
            # --- Hafıza: Son 10 mesajı topla
            all_msgs = chat_log[client_id]["messages"]
            sorted_keys = sorted(map(int, all_msgs.keys()))
            recent_msgs = sorted_keys[-10:]

            history_text = ""
            for key in recent_msgs:
                m = all_msgs[str(key)]
                who = "Kullanıcı" if m["role"] == "user" else "Bot"
                history_text += f"{who}: {m['content']}\n"

            # --- Embedding oluştur
            enriched_input = f"{history_text.strip()}\nSon mesaj: {req_msg}"
            resp = await client.embeddings.create(
                model="text-embedding-3-small",
                input=enriched_input
            )
            user_vec = np.array(resp.data[0].embedding, dtype=np.float32)

            # --- En uygun ürünü bul
            best, best_score = None, -1.0
            with SessionLocal() as db:
                for p in db.query(Product).filter(Product.embedding.isnot(None)):
                    prod_vec = np.frombuffer(p.embedding, dtype=np.float32)
                    sim = cosine(user_vec, prod_vec)
                    if sim > best_score:
                        best, best_score = p, sim

            # --- Model yanıtı oluştur
            if best:
                prompt_text = (
                    "Aşağıda bir müşterinin son konuşmaları ve tasarım isteği yer almaktadır.\n"
                    "Ayrıca ürünlerimizden biri olan aşağıdaki açıklamayı da göz önünde bulundurarak, müşterinin ihtiyacına en uygun çözümü öner.\n\n"
                    f"Kullanıcı konuşma geçmişi:\n{history_text.strip()}\n\n"
                    f"Tasarım isteği:\n{req_msg}\n\n"
                    f"İlgili ürün açıklaması:\n{best.description}\n\n"
                    "Yanıt:"
                )

                bot_reply = await mm.get_ai_response(req_msg, prompt=prompt_text)
            else:
                bot_reply = "Tasarım isteğinizi anladım, ancak şu anda size uygun bir ürün belirleyemedim. Daha fazla detay verebilir misiniz?"

        elif msg_type == "fiyat_sorgusu":
            bot_reply = (
                "Dilerseniz daha detaylı bilgi için bizimle iletişime geçebilirsiniz:\n"
                "📞 <a href='tel:+905356647752'>+90 535 664 77 52</a>\n"
                "📞 <a href='tel:+902163790708'>+90 216 379 07 08</a>"
            )


        elif msg_type == "stok_sorgusu":
            bot_reply = await mm.get_ai_response(
            req_msg, prompt=prompt["selection"]["stok_sorgusu"]["tr"]
        )

        elif msg_type == "teslimat_sorgusu":
            bot_reply = (
                "Üretim süreçleri ve teslimat bilgisi için lütfen bize ulaşın!\n"
                "📞 <a href='tel:+905356647752'>+90 535 664 77 52</a>\n"
                "📞 <a href='tel:+902163790708'>+90 216 379 07 08</a>"
            )
        elif msg_type == "kargo":
            bot_reply = (
                "Üretim süreçleri ve teslimat bilgisi için lütfen bize ulaşın!\n"
                "📞 <a href='tel:+905356647752'>+90 535 664 77 52</a>\n"
                "📞 <a href='tel:+902163790708'>+90 216 379 07 08</a>"
            )

        elif msg_type == "destek_talebi":
            bot_reply = (
                "Bize doğrudan ulaşmak isterseniz aşağıdaki numaralardan bize ulaşabilirsiniz:\n"
                "📞 <a href='tel:+905356647752'>+90 535 664 77 52</a>\n"
                "📞 <a href='tel:+902163790708'>+90 216 379 07 08</a>"
            )

        elif msg_type == "müşteri_temsili":
            bot_reply = (
                "Bize doğrudan ulaşmak isterseniz aşağıdaki numaralardan bize ulaşabilirsiniz:\n"
                "📞 <a href='tel:+905356647752'>+90 535 664 77 52</a>\n"
                "📞 <a href='tel:+902163790708'>+90 216 379 07 08</a>"
            )

        elif msg_type == "örnek_istemi":
            bot_reply = (
                "Önceki işlerimizi incelemek isterseniz örnek projelerimize göz atabilirsiniz:\n"
                "<a href='https://eymenreklam.com/%C3%BCr%C3%BCn-kategori/projeler/' target='_blank'>eymenreklam.com/projeler</a>"
            )

        elif msg_type == "hizmet_ögrenme":
            # 1. Embedding oluştur
            resp = await client.embeddings.create(
                model="text-embedding-3-small",
                input=req_msg
            )
            user_vec = np.array(resp.data[0].embedding, dtype=np.float32)

            # 2. En yakın ürünü bul (isim üzerinden)
            best, best_score = None, -1.0
            with SessionLocal() as db:
                for p in db.query(Product).filter(Product.embedding.isnot(None)):
                    prod_vec = np.frombuffer(p.embedding, dtype=np.float32)
                    sim = cosine(user_vec, prod_vec)
                    if sim > best_score:
                        best, best_score = p, sim

            # 3. Uygun ürün bulunduysa modelden detaylı açıklama iste
            if best:
                prompt_text = (
                    "Aşağıda bir müşteri mesajı ve ona uygun ürünün açıklaması verilmiştir.\n"
                    "Müşterinin ne istediğini ürün bilgisine göre değerlendir ve açıklayıcı, ikna edici bir yanıt ver.\n\n"
                    f"Müşteri mesajı:\n{req_msg}\n\n"
                    f"Ürün açıklaması:\n{best.description}\n\n"
                    "Yanıt:"
                )

                bot_reply = await mm.get_ai_response(req_msg, prompt=prompt_text)
            else:
                bot_reply = "Şu an için ilgili hizmete dair bir ürün bulamadım. Hangi konuda bilgi almak istediğinizi detaylandırabilir misiniz?"


        elif msg_type == "sohbet":
            all_msgs = chat_log[client_id]["messages"]
            sorted_keys = sorted(map(int, all_msgs.keys()))
            recent_msgs = sorted_keys[-10:]

            history_text = ""
            for key in recent_msgs:
                m = all_msgs[str(key)]
                who = "Kullanıcı" if m["role"] == "user" else "Bot"
                history_text += f"{who}: {m['content']}\n"

            prompt_text = prompt["chat"]["connect"]["tr"].replace("{}", history_text.strip())
            bot_reply = await mm.get_ai_response(req_msg, prompt=prompt_text)

        else:
            bot_reply = "Mesajınızı tam anlayamadım. Ne hakkında konuşmak istersiniz?"

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
        import traceback
        print("❌ chat_handler hatası:")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Sunucuda beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyin."
        )
