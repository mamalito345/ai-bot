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
        # Son 10 mesajı al
        all_msgs = chat_log[client_id]["messages"]
        sorted_keys = sorted(map(int, all_msgs.keys()))
        last_keys = sorted_keys[-10:]

        # Geçmişi birleştir
        history_text = ""
        for key in last_keys:
            m = all_msgs[str(key)]
            who = "Kullanıcı" if m["role"] == "user" else "Bot"
            history_text += f"{who}: {m['content']}\n"

        # Konuşma geçmişi + kullanıcı mesajını birleştir
        full_message = f"{history_text.strip()}\nKullanıcı: {req_msg.strip()}"

        # AI'dan mesaj türünü belirlemesini iste
        msg_type = await mm.get_ai_response(
            user_message=full_message,
            system_prompt=prompt["selection"]["product"]["tr"]
        )
        
        if msg_type == "[sohbet]":
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
            

        elif msg_type == "[ürün_isteği]":
            with SessionLocal() as db:
                product_names = [name for (name,) in db.query(Product.name).all()]
                product_count = db.query(Product).count()
                print(f"Toplam ürün sayısı: {product_count}")

            if not product_names:
                bot_reply = "Şu anda elimizde listelenmiş bir ürün bulunmamaktadır."
            else:
                product_list_text = "\n".join([f"- {name}" for name in product_names])
                full_prompt = (
                    "Sen bir satış danışmanısın. aşşağıda elimizde buluna ürün kategoryleri linkleri bulunkata bu kategorylerden hangisine daha yankınsa müşterinin isteği o kategory linkini at. vericeğin mesaj 2 cümleden oluşsun. ürünlerimizi burdan inceleyebilirsiniz ve link"
                    "https://eymenreklam.com/urun-kategori/tabela/"
                    "https://eymenreklam.com/urun-kategori/arac-folyo-kaplama/"
                    "https://eymenreklam.com/urun-kategori/branda-bez-afis-baski/"
                    "https://eymenreklam.com/urun-kategori/cephe-giydirme/"
                    "https://eymenreklam.com/urun-kategori/folyo-etiket-kesim/"
                    "https://eymenreklam.com/urun-kategori/cam-folyo-uygulamalari/"
                    "https://eymenreklam.com/urun-kategori/lightbox-uygulamalari/"
                    "https://eymenreklam.com/urun-kategori/cut-out-maket/"
                    "https://eymenreklam.com/urun-kategori/fotoblok-baski/"
                    "https://eymenreklam.com/urun-kategori/magaza-reklam-uygulamalari/"
                    "https://eymenreklam.com/urun-kategori/is-guvenlik-levhalari/"
                    "https://eymenreklam.com/urun-kategori/display-urunler/"
                )

                user_prompt = req_msg.strip()

                bot_reply = await mm.get_ai_response(
                    user_message=user_prompt,
                    system_prompt=full_prompt
                )
        elif msg_type == "[tasarım_isteği]":
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
                full_prompt = (
                    "Sen eymen reklema ajansının yapayzeka canlı destek asistansın. Kullanıcının yaptığı görüşme geçmişi ve "
                    "Kibar ve nazik ol yapayzeka asistanı olsanda iyimisin gibi insanni sorualra olabildiğince insamış gibi cevapver insan gibi hissettir\n\n"
                    "linkler üzerindne inceleyebilirsini de. tasarımın olabileceği en yakın linki at"
                    "https://eymenreklam.com/urun-kategori/tabela/"
                    "https://eymenreklam.com/urun-kategori/arac-folyo-kaplama/"
                    "https://eymenreklam.com/urun-kategori/branda-bez-afis-baski/"
                    "https://eymenreklam.com/urun-kategori/cephe-giydirme/"
                    "https://eymenreklam.com/urun-kategori/folyo-etiket-kesim/"
                    "https://eymenreklam.com/urun-kategori/cam-folyo-uygulamalari/"
                    "https://eymenreklam.com/urun-kategori/lightbox-uygulamalari/"
                    "https://eymenreklam.com/urun-kategori/cut-out-maket/"
                    "https://eymenreklam.com/urun-kategori/fotoblok-baski/"
                    "https://eymenreklam.com/urun-kategori/magaza-reklam-uygulamalari/"
                    "https://eymenreklam.com/urun-kategori/is-guvenlik-levhalari/"
                    "https://eymenreklam.com/urun-kategori/display-urunler/"
                    f"Konuşma Geçmişi:\n{history_text.strip()}"
                )

                # 5. AI'dan cevap al
                bot_reply = await mm.get_ai_response(
                    user_message=req_msg,
                    system_prompt=full_prompt
                )

        elif msg_type == "[fiyat_sorgusu]":
            product_links = {
                "Tabela": "https://eymenreklam.com/urun-kategori/tabela/",
                "Araç Folyo Kaplama": "https://eymenreklam.com/urun-kategori/arac-folyo-kaplama/",
                "Branda Bez Afiş Baskı": "https://eymenreklam.com/urun-kategori/branda-bez-afis-baski/",
                "Cephe Giydirme": "https://eymenreklam.com/urun-kategori/cephe-giydirme/",
                "Folyo Etiket Kesim": "https://eymenreklam.com/urun-kategori/folyo-etiket-kesim/",
                "Cam Folyo Uygulamaları": "https://eymenreklam.com/urun-kategori/cam-folyo-uygulamalari/",
                "Lightbox Uygulamaları": "https://eymenreklam.com/urun-kategori/lightbox-uygulamalari/",
                "Cut Out Maket": "https://eymenreklam.com/urun-kategori/cut-out-maket/",
                "Fotoblok Baskı": "https://eymenreklam.com/urun-kategori/fotoblok-baski/",
                "Mağaza Reklam Uygulamaları": "https://eymenreklam.com/urun-kategori/magaza-reklam-uygulamalari/",
                "İş Güvenlik Levhaları": "https://eymenreklam.com/urun-kategori/is-guvenlik-levhalari/",
                "Display Ürünler": "https://eymenreklam.com/urun-kategori/display-urunler/"
            }

            # Son 3 mesaj + şu anki mesaj
            all_msgs = chat_log[client_id]["messages"]
            sorted_keys = sorted(map(int, all_msgs.keys()))
            recent_msgs = [all_msgs[str(k)]["content"] for k in sorted_keys[-3:]]
            recent_msgs.append(req_msg)
            full_convo = "\n".join(recent_msgs)

            # AI'ye verilecek prompt
            full_prompt = (
                "Sen bir reklam firmasında çalışan satış temsilcisisin. Müşteriyle aranda geçen mesajlaşmalar aşağıda verilmiştir.\n"
                "Müşterinin fiyatını sorduğu ürünü belirle ve aşağıdaki ürün listesinde bu ürünün linkini bul.\n"
                "Cevap olarak sadece bu yapıyı gönder:\n"
                "\n"
                "Ürün: [ürün adı]\n"
                "Link: [link]\n\n"
                "İletişim numaraları:\n"
                "📞 +90 535 664 77 52\n"
                "📞 +90 216 379 07 08\n\n"
                "Sadece aşağıdaki ürünlerden biri olabilir:\n" +
                "\n".join([f"- {key}: {url}" for key, url in product_links.items()]) +
                "\n\nMesajlar:\n" + full_convo
            )

            ai_output = await mm.get_ai_response(req_msg, system_prompt=full_prompt)
            bot_reply = ai_output.strip()


            
        elif msg_type == "[müşteri_temsili]":
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
            full_prompt = (
                "Sen bir satış sonrası destek asistanısın. Aşağıda müşteri ile yapılan son konuşma yer almakta.\n"
                "Müşteri bir sorun ya da şikayet bildiriyor olabilir.\n"
                "Bu gibi durumlarda kullanıcıyı doğrudan iletişim numaralarına yönlendirmelisin.\n"
                "Kibar, ilgili ve profesyonel bir şekilde mesaj ver.\n\n"
                "Kibar ve nazik ol yapayzeka asistanı olsanda iyimisin gibi insanni sorualra olabildiğince insamış gibi cevapver insangibi hissettir\n\n"
                "İletişim numaraları:\n"
                "📞 +90 535 664 77 52\n"
                "📞 +90 216 379 07 08\n\n"
                f"Konuşma Geçmişi:\n{history_text.strip()}"
            )

            # AI yanıtı üret
            bot_reply = await mm.get_ai_response(
                user_message=req_msg.strip(),
                system_prompt=full_prompt
            )
        elif msg_type == "[örnek_istemi]":
            bot_reply = (
                "Daha önce yaptığımız örnek işleri incelemek için aşağıdaki bağlantıya göz atabilirsiniz:\n"
                "👉 https://eymenreklam.com/urun-kategori/projeler/\n\n"
                "İlgilendiğiniz özel bir hizmet varsa, o alanda da örnek sunabilirim. 😊"
            )

        elif msg_type == "[hizmet_ögrenme]":
            bot_reply = (
                "Tüm ürün ve hizmetlerimizi aşağıdaki bağlantıdan inceleyebilirsiniz:\n"
                "👉 https://eymenreklam.com/shop/\n\n"
                "Merak ettiğiniz özel bir ürün varsa detaylıca yardımcı olabilirim. 😊"
            )
        print(msg_type)
        messages = chat_log[client_id]["messages"]
        next_idx = str(max(map(int, messages.keys()), default=-1) + 1)

        # --- Kullanıcı mesajını ekle
        messages[next_idx] = {
            "role": "bot",
            "content": bot_reply,
            "timestamp": datetime.now().isoformat()
        }
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
