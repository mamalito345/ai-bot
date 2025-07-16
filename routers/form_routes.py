from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText

router = APIRouter()

class ContactForm(BaseModel):
    name: str
    email: EmailStr
    company: str
    project: str
    client_id: str

@router.post("/form")
async def handle_form(form: ContactForm):
    try:
        # Mail içeriği
        body = f"""
        Yeni Form Başvurusu

        Ad: {form.name}
        E-posta: {form.email}
        Şirket: {form.company}
        Proje Detayı: {form.project}
        Client ID: {form.client_id}
        """

        msg = MIMEText(body)
        msg["Subject"] = "Yeni Form Başvurusu"
        msg["From"] = "botc2262@gmail.com"
        msg["To"] = "ramazan@eymenajans.com.tr"

        # Mail gönderimi (SMTP ayarlarını değiştir)
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login("botc2262@gmail.com", "wejhzzijowvtyomb")
            server.send_message(msg)

        return {"success": True, "message": "Form gönderildi."}
    
    except Exception as e:
        return {"success": False, "message": "Mail gönderilemedi.", "error": str(e)}
