from fastapi import APIRouter
from pydantic import BaseModel
import json
import os

router = APIRouter()

CHAT_INFO_FILE = "chat_info.json"


class UserInfo(BaseModel):
    client_id: str
    name: str
    phone: str


@router.post("/save-user-info")
async def save_user_info(info: UserInfo):
    # Eğer dosya yoksa boş bir sözlük oluştur
    if not os.path.exists(CHAT_INFO_FILE):
        with open(CHAT_INFO_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

    # Dosyadaki veriyi oku
    with open(CHAT_INFO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Eğer client_id zaten varsa ekleme
    if info.client_id in data:
        return {"status": "already exists"}

    # Yeni veriyi ekle
    data[info.client_id] = {
        "name": info.name,
        "phone": info.phone
    }

    # Dosyaya geri yaz
    with open(CHAT_INFO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"status": "saved"}

