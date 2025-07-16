from fastapi import FastAPI
from routers.chat import router as chat_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS (geliştirme için herkes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ana router
app.include_router(chat_router)
@app.get("/")
def root():
    return {"message": "API is running"}
