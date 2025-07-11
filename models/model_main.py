from openai import AsyncOpenAI
from app.config import settings
from sqlalchemy.orm import Session
import numpy as np
import asyncio
from models.db_models import Product  # yolunu kendi projenize göre ayarlayın
from database.db import SessionLocal  # sync session
 
client = AsyncOpenAI(api_key=settings.openai_api_key)

async def get_ai_response(user_message: str, system_prompt: str) -> str:
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # o4-mini model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.2
        )
        usage = response.usage  # type: openai.types.CompletionUsage
        if usage:
            print(f"[TOKEN] prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens}, total: {usage.total_tokens}")


        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Hata oluştu: {str(e)}"


async def generate_embeddings_for_summaries() -> None:
    with SessionLocal() as session:
        products = session.query(Product).filter(Product.embedding.is_(None)).all()

        for product in products:
            text = (product.description or product.short_description or product.name).strip()
            if not text:
                continue

            # ⬇️ await ile çağır
            resp = await client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            emb = resp.data[0].embedding
            print("çalıştı_emb")

            product.embedding = np.array(emb, dtype=np.float32).tobytes()

        session.commit()



