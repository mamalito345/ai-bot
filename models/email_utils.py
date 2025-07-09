from email.message import EmailMessage
from aiosmtplib import send
from typing import List

async def forward_user_info_to_admin(user_mail: str, user_name: str, admin_mail: str):
    msg = EmailMessage()
    msg["From"] = "botc2262@gmail.com"     # Bu senin sabit Gmail hesabın
    msg["To"] = "mamalito1453a@gmail.com"                      # Bu da WP panelinden gelen hedef mail
    msg["Subject"] = "Yeni Chatbot Kullanıcısı"

    msg.set_content(
        f"Kullanıcı E-Posta: {user_mail}\n"
        f"Kullanıcı İsmi   : {user_name}\n"
        f"Bot Gönderici    : botc2262@gmail.com"
    )

    await send(
        msg,
        hostname="smtp.gmail.com",
        port=587,
        start_tls=True,
        username="botc2262@gmail.com",
        password="jipkskozrxdhacyp"  # ← oluşturduğun 16 karakterlik şifre
    )

async def forward_user_message_to_admin(
    user_mail: str,
    user_name: str,
    admin_mail: str,
    messages: List[str],
    bot_replies: List[str]
):
    msg = EmailMessage()
    msg["From"] = "botc2262@gmail.com"
    msg["To"] = "mamalito1453a@gmail.com"  # dışarıdan gelen admin_mail burada doğru kullanılıyor
    msg["Subject"] = "Yeni Chatbot Kullanıcısı (Mesaj + Cevap)"

    # Kullanıcı mesajları
    user_lines = "\n".join(f"{i+1}. {m}" for i, m in enumerate(messages))

    # Bot cevapları
    bot_lines = "\n".join(f"{i+1}. {r}" for i, r in enumerate(bot_replies))

    msg.set_content(
        f"📬 Yeni chatbot etkileşimi:\n\n"
        f"👤 Kullanıcı İsmi   : {user_name}\n"
        f"✉️  Kullanıcı E-Posta: {user_mail}\n"
        f"🤖 Bot Gönderici    : botc2262@gmail.com\n\n"
        f"🗨️ Kullanıcının İlk 4 Mesajı:\n{user_lines}\n\n"
        f"💬 Bot Cevapları:\n{bot_lines}"
    )
    print("nolur")
    await send(
        msg,
        hostname="smtp.gmail.com",
        port=587,
        start_tls=True,
        username="botc2262@gmail.com",
        password="jipkskozrxdhacyp"
    )