from database.db import Base, engine
import models.db_models  # BU SATIR OLMADAN tablo oluşmaz

Base.metadata.create_all(bind=engine)
print("✅ products tablosu oluşturuldu.")