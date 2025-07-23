import asyncio
from openai import AsyncOpenAI
from app.config import settings
from pathlib import Path
prompt_path = Path(__file__).parent / "prompt.txt"


client = AsyncOpenAI(api_key=settings.openai_api_key)


async def get_ai_response(user_message: str, ready_prompt: str) -> str:
    if prompt_path.exists():
        system_prompt = prompt_path.read_text(encoding="utf-8")
    else:
        system_prompt = "Eymen Reklam Asistanı sistem promptu eksik."
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": ready_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Hata oluştu: {str(e)}"


