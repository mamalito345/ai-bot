import os
from database.db import Base, engine
from models import db_models

DB_PATH = "chatbot.db"  # settings.database_url içinde sqlite:///./chatbot.db ise dosya adı budur
def reset():
    if os.path.exists(DB_PATH):
        print("🗑️ Eski veritabanı siliniyor...")
        os.remove(DB_PATH)
    else:
        print("📂 Veritabanı zaten yok, temiz başlangıç yapılıyor...")

    print("🔧 Tablolar yeniden oluşturuluyor...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablolar başarıyla oluşturuldu.")
