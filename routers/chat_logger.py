from fastapi import APIRouter, Request
from pydantic import BaseModel
import smtplib
from email.mime.text import MIMEText

router = APIRouter()

class ChatData(BaseModel):
    client_id: str
    messages: list[str]

@router.post("/send-chat")
async def send_chat_log(data: ChatData):
    message_body = "\n\n".join(data.messages)
    
    msg = MIMEText(f"Kullanıcı ID: {data.client_id}\n\nSohbet:\n{message_body}", "plain", "utf-8")
    msg["Subject"] = "Kapanışta Chat Logu"
    msg["From"] = "botc2262@gmail.com"
    msg["To"] = "ramazan@eymenajans.com.tr"

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("botc2262@gmail.com", "wejhzzijowvtyomb")
        server.send_message(msg)
        server.quit()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
