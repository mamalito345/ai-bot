from fastapi import APIRouter, Request
import smtplib
from email.mime.text import MIMEText
import json

router = APIRouter()

@router.post("/send-chat")
async def send_chat(request: Request):
    try:
        raw_body = await request.body()
        print("📦 GÖNDERİLEN RAW BODY:", raw_body)  # 💥 Debug: gelen veri ham haliyle
        decoded = raw_body.decode("utf-8")
        print("🧩 DECODED BODY:", decoded)  # 💥 Debug: string hali
        data = json.loads(decoded)
        print("📘 PARSED JSON:", data)  # 💥 Debug: JSON objesi
    except Exception as e:
        print("❌ PARSE HATASI:", str(e))
        return {"status": "parse_error", "detail": str(e)}

    client_id = data.get("client_id")
    messages = data.get("messages", [])

    print("🧑‍💻 client_id:", client_id)
    print("💬 messages:", messages)

    if not messages:
        print("❗ Mesaj listesi boş!")
        return {"status": "no messages"}

    # E-posta içeriği
    content = f"📩 Yeni mesajlar (client_id: {client_id}):\n\n"
    for m in messages:
        role = m["sender"]
        text = m["text"]
        content += f"[{role.upper()}] {text}\n"

    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = f"Chat Log - {client_id}"
    msg["From"] = "botc2262@gmail.com"
    msg["To"] = "info@eymenreklam.com"

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login("botc2262@gmail.com", "wejhzzijowvtyomb")
            smtp.send_message(msg)
        print("✅ Mail başarıyla gönderildi.")
        return {"status": "sent"}
    except Exception as e:
        print("❌ Mail gönderme hatası:", str(e))
        return {"status": "email_error", "detail": str(e)}
