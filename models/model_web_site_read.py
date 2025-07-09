from app import config
from service import service_web_site_read as sr
from database.db import SessionLocal, Base, engine
import model_main as ai
import time as t
import json
from bs4 import BeautifulSoup
import asyncio
from models import db_models 
proses = "none"
Base.metadata.create_all(bind=engine)
settings = config.settings

db = SessionLocal()

Base.metadata.create_all(bind=engine)
print("✅ Tablolar oluşturuldu.")

def temizle_html(html):
    return BeautifulSoup(html, "html.parser").get_text().strip()


web_data = sr.WordPressReader(
    base_url=settings.base_url,
    consumer_key=settings.woo_cus,
    consumer_secret=settings.woo_secret
)

products = web_data.get_products()
t.sleep(1)



with open("prompt.json", "r", encoding="utf-8") as f:
    prompt = json.load(f)

for p in products:
    summary = asyncio.run(
        ai.get_ai_response(
            temizle_html(p.get("description", "")),
            prompt["model_web_site_read"]["product"]["tr"],
        )
    )
    short_summary = asyncio.run(
        ai.get_ai_response(
            temizle_html(p.get("short_description", "")),
            prompt["model_web_site_read"]["product"]["tr"],
        )
    )

    new = db_models.Product(
        id=p["id"],
        name=p["name"],
        description=summary,
        short_description=short_summary,   # yazım hatası düzeltildi
        permalink=p.get("permalink", ""),
    )
    db.add(new)
    db.commit()
    db.refresh(new)
proses = "done"
db.close()

