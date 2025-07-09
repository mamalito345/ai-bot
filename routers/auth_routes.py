from fastapi import APIRouter
from typing import List
from pydantic import BaseModel, EmailStr
from models.email_utils import forward_user_info_to_admin, forward_user_message_to_admin

router = APIRouter()

class UserInfo(BaseModel):
    mail: EmailStr
    isim: str
    sirketmail: EmailStr

class UserMessagePayload(BaseModel):
    mail: EmailStr
    isim: str
    sirketmail: EmailStr
    mesajlar: List[str]
    botcevaplar: List[str]  # ✅ yeni eklendi

@router.post("/register")
async def receive_user_info(data: UserInfo):
    await forward_user_info_to_admin(
        user_mail=data.mail,
        user_name=data.isim,
        admin_mail=data.sirketmail
    )
    return {"message": "Kullanıcı bilgisi gönderildi"}

@router.post("/message")
async def receive_user_messages(data: UserMessagePayload):
    await forward_user_message_to_admin(
        user_mail=data.mail,
        user_name=data.isim,
        admin_mail=data.sirketmail,
        messages=data.mesajlar,
        bot_replies=data.botcevaplar  # ✅ yeni eklendi
    )
    return {"message": "Kullanıcı ve bot mesajları gönderildi"}
