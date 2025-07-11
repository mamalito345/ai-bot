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

        # Kullanıcı ilk defa geliyorsa messages ve state alanlarını oluştur
        if client_id not in chat_log:
            chat_log[client_id] = {
                "messages": {},
                "state": {
                    "ad": None,
                    "son_intent": None,
                    "son_urun": None,
                    "sorun_durumu": None,
                    "ozel_not": None
                }
            }

        # Eğer eski veride sadece messages varsa, state'i sonradan da ekleyelim (geriye dönük uyumluluk)
        elif "state" not in chat_log[client_id]:
            chat_log[client_id]["state"] = {
                "ad": None,
                "son_intent": None,
                "son_urun": None,
                "sorun_durumu": None,
                "ozel_not": None
            }

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
            req_msg, system_prompt=prompt["selection"]["product"]["tr"]
        )
        if msg_type == "sohbet":
            all_msgs = chat_log[client_id]["messages"]
            sorted_keys = sorted(map(int, all_msgs.keys()))
            last_keys = sorted_keys[-10:]  # En fazla 10, yoksa olan kadar

            history_text = ""
            for key in last_keys:
                m = all_msgs[str(key)]
                who = "Kullanıcı" if m["role"] == "user" else "Bot"
                history_text += f"{who}: {m['content']}\n"

            full_prompt = (
                prompt["chat"]["product"]["tr"].strip() + "\n\n" +
                prompt["chat"]["connect"]["tr"].replace("{}", history_text.strip())
            )
            bot_reply = await mm.get_ai_response(user_message=req_msg, system_prompt=full_prompt)

        elif msg_type == "ürün_isteği":
            with SessionLocal() as db:
                product_names = [p.name for p in db.query(Product).all()]

            if not product_names:
                bot_reply = "Şu anda elimizde listelenmiş bir ürün bulunmamaktadır."
            else:
                product_list_text = "\n".join([f"- {name}" for name in product_names])
                prompt = (
                    "Sen bir satış danışmanısın. Aşağıda elimizde bulunan ürünlerin listesi yer almakta. Bulardan hangileri kullanıcının istediği ürünle örtüşüyorsa elimizde şu ürünler var şeklinde ürünleri yaz.\n"
                    f"Ürün Listesi:\n{product_list_text}"
                )

                user_prompt = req_msg.strip()

                bot_reply = await mm.get_ai_response(
                    user_message=user_prompt,
                    system_prompt=prompt
                )
        elif msg_type == "tasarım_isteği":
            # 1. Ürünleri veritabanından al
            with SessionLocal() as db:
                products = db.query(Product).all()

            if not products:
                bot_reply = "Şu anda elimizde tasarım uygulanabilecek bir ürün görünmüyor."
            else:
                # 2. Ürün listesi (adı + kısa açıklama)
                product_text = ""
                for p in products:
                    info = p.short_description or p.description or "Bilgi yok"
                    product_text += f"- {p.name}: {info.strip()}\n"

                # 3. Son 10 mesajı al
                all_msgs = chat_log[client_id]["messages"]
                sorted_keys = sorted(map(int, all_msgs.keys()))
                last_keys = sorted_keys[-10:]

                history_text = ""
                for key in last_keys:
                    m = all_msgs[str(key)]
                    who = "Kullanıcı" if m["role"] == "user" else "Bot"
                    history_text += f"{who}: {m['content']}\n"

                # 4. Sistem promptu oluştur
                prompt = (
                    "Sen bir tasarım danışmanı asistansın. Kullanıcının yaptığı görüşme geçmişi ve "
                    "tasarım talebine göre aşağıdaki ürünlerden hangisinin bu isteğe uygun olduğunu belirle.\n"
                    "Ayrıca kullanıcıya yönlendirici ve açıklayıcı bir cevap ver.\n\n"
                    f"Ürün Listesi:\n{product_text.strip()}\n\n"
                    f"Konuşma Geçmişi:\n{history_text.strip()}"
                )

                # 5. AI'dan cevap al
                bot_reply = await mm.get_ai_response(
                    user_message=req_msg,
                    system_prompt=prompt
                )
         
        elif msg_type == "fiyat_sorgusu":
            with SessionLocal() as db:
                products = db.query(Product).all()

            if not products:
                bot_reply = "Şu anda elimizde fiyat bilgisi verilebilecek ürün bulunmamaktadır."
            else:
                # 1. Ürün listesi (kısa açıklamalarla)
                product_text = ""
                for p in products:
                    desc = p.short_description or p.description or "Açıklama yok"
                    product_text += f"- {p.name}: {desc.strip()}\n"

                # 2. Kullanıcının son 10 mesajı
                all_msgs = chat_log[client_id]["messages"]
                sorted_keys = sorted(map(int, all_msgs.keys()))
                last_keys = sorted_keys[-10:]

                history_text = ""
                for key in last_keys:
                    m = all_msgs[str(key)]
                    who = "Kullanıcı" if m["role"] == "user" else "Bot"
                    history_text += f"{who}: {m['content']}\n"

                # 3. Sistem mesajı
                prompt = (
                    "Sen bir satış asistanısın. Müşteri bir ürünün fiyatını sordu.\n"
                    "Aşağıda elimizdeki ürünlerin kısa açıklamalarıyla birlikte listesi var.\n"
                    "Ve ayrıca kullanıcı ile yaptığın son konuşmalar yer almakta.\n\n"
                    "Görevin şunlar:\n"
                    "1. Son konuşmalara ve mesaja göre müşteri hangi ürünü istiyor, belirle.\n"
                    "2. Eğer istediği ürün için birden fazla seçenek varsa (tabela isterse ama elimizde birden fazal tabela varsa ve diğer birden fazla olan ürünler için) hangi ürünü sipesifik olarak sorduğunu öğrenmek için olası ürünlerin listesini gönder.\n"
                    "3. Eğer mesaj netse ve tek ürünse, ürünün açıklaması üzerindne ürünün fiyatını etkileyebilecek faktörleri madde madde yaz. kesinlikle asla fiyat verme \n\n"
                    f"Ürün Listesi:\n{product_text.strip()}\n\n"
                    f"Konuşma Geçmişi:\n{history_text.strip()}"
                )

                # 4. AI yanıtı
                bot_reply = await mm.get_ai_response(
                    user_message=req_msg.strip(),
                    system_prompt=prompt
                )
        elif msg_type == "müşteri_temsili":
            # Son 10 mesajı al
            all_msgs = chat_log[client_id]["messages"]
            sorted_keys = sorted(map(int, all_msgs.keys()))
            last_keys = sorted_keys[-10:]

            history_text = ""
            for key in last_keys:
                m = all_msgs[str(key)]
                who = "Kullanıcı" if m["role"] == "user" else "Bot"
                history_text += f"{who}: {m['content']}\n"

            # Sistem prompt
            prompt = (
                "Sen bir satış sonrası destek asistanısın. Aşağıda müşteri ile yapılan son konuşma yer almakta.\n"
                "Müşteri bir sorun ya da şikayet bildiriyor olabilir.\n"
                "Bu gibi durumlarda kullanıcıyı doğrudan iletişim numaralarına yönlendirmelisin.\n"
                "Kibar, ilgili ve profesyonel bir şekilde mesaj ver.\n\n"
                "İletişim numaraları:\n"
                "📞 +90 535 664 77 52\n"
                "📞 +90 216 379 07 08\n\n"
                f"Konuşma Geçmişi:\n{history_text.strip()}"
            )

            # AI yanıtı üret
            bot_reply = await mm.get_ai_response(
                user_message=req_msg.strip(),
                system_prompt=prompt
            )
        if msg_type == "örnek_istemi":
            # 1. Ürün isimlerini veritabanından al
            with SessionLocal() as db:
                product_names = [p.name for p in db.query(Product).all()]

            # 2. Son 10 mesajı al
            all_msgs = chat_log[client_id]["messages"]
            sorted_keys = sorted(map(int, all_msgs.keys()))
            last_keys = sorted_keys[-10:]

            history_text = ""
            for key in last_keys:
                m = all_msgs[str(key)]
                who = "Kullanıcı" if m["role"] == "user" else "Bot"
                history_text += f"{who}: {m['content']}\n"

            # 3. Sistem prompt
            prompt = (
                "Sen bir reklam firmasında çalışan dijital asistan botsun. Kullanıcıyla yapılan son görüşmeler aşağıda verilmiştir.\n"
                "Kullanıcı örnek işler görmek istiyor. Aşağıda firmanın sunduğu ürünlerin isimleri de yer alıyor.\n"
                "Amacın, konuşma geçmişine ve son mesaja göre kullanıcı hangi ürünün örneklerini görmek istiyor, bunu tahmin etmektir.\n\n"
                "Eğer örnek istenen şey 'market', 'mağaza', 'dükkan', 'tabela' gibi genelse, bu bağlantıyı öner:\n"
                "👉 https://eymenreklam.com/urun-kategori/projeler/\n\n"
                "Cevabı tamamen sen üret. Açıklayıcı, yönlendirici ve nazik bir mesaj yaz.\n\n"
                f"Ürün Listesi:\n{', '.join(product_names)}\n\n"
                f"Konuşma Geçmişi:\n{history_text.strip()}"
            )

            # 4. AI yanıtı
            bot_reply = await mm.get_ai_response(
                user_message=req_msg.strip(),
                system_prompt=prompt
            )
        elif msg_type == "hizmet_ögrenme":
            # 1. Ürün adı ve permalinklerini al
            with SessionLocal() as db:
                products = db.query(Product).all()

            if not products:
                bot_reply = "Şu anda sunulan hizmet bilgileri sistemde yer almıyor."
            else:
                # 2. Ürün adı + link formatla
                product_list_text = "\n".join(
                    [f"- {p.name}: {p.permalink}" for p in products if p.permalink]
                )

                # 3. Son 10 mesajı al
                all_msgs = chat_log[client_id]["messages"]
                sorted_keys = sorted(map(int, all_msgs.keys()))
                last_keys = sorted_keys[-10:]

                history_text = ""
                for key in last_keys:
                    m = all_msgs[str(key)]
                    who = "Kullanıcı" if m["role"] == "user" else "Bot"
                    history_text += f"{who}: {m['content']}\n"

                # 4. Sistem prompt
                prompt = (
                    "Sen bir reklam firmasında çalışan dijital asistansın. Kullanıcının son mesajları aşağıda yer alıyor.\n"
                    "Ayrıca elimizdeki ürünlerin adları ve sayfa bağlantıları da listelendi.\n\n"
                    "Eğer kullanıcı belirli bir ürünle ilgileniyorsa, ilgili ürünün bağlantısını mesajda ver.\n"
                    "Eğer genel bilgi istiyorsa, şu kategori sayfasına yönlendir:\n"
                    "👉 https://eymenreklam.com/urun-kategori\n\n"
                    "Cevabın sade, açıklayıcı ve yönlendirici olsun.\n\n"
                    f"Ürün Listesi:\n{product_list_text.strip()}\n\n"
                    f"Konuşma Geçmişi:\n{history_text.strip()}"
                )

                # 5. AI yanıtı
                bot_reply = await mm.get_ai_response(
                    user_message=req_msg.strip(),
                    system_prompt=prompt
                )
        return ChatResponse(reply=bot_reply)
    except Exception as e:
        import traceback
        print("❌ chat_handler hatası:")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Sunucuda beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyin."
        )
