from database.db import SessionLocal
from models.db_models import Product

db = SessionLocal()
products = db.query(Product).all()
print(f"{len(products)} ürün bulundu.")
for p in products:
    print(f"ID: {p.id}")
    print(f"İsim: {p.name}")
    print(f"Kısa Açıklama: {p.short_description}")
    print(f"Açıklama: {p.description}")
    print("-" * 50)
db.close()
