from fastapi import APIRouter, Request
import smtplib
from email.mime.text import MIMEText

router = APIRouter()

@router.post("/send-chat")
async def send_chat(request: Request):
    data = await request.json()
    client_id = data.get("client_id")
    messages = data.get("messages", [])

    if not messages:
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
    msg["To"] = "ramazan@eymenajans.com.tr"

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login("botc2262@gmail.com", "wejhzzijowvtyomb")
            smtp.send_message(msg)
        return {"status": "sent"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
