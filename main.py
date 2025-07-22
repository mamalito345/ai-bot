from fastapi import FastAPI
from routers.chat import router as chat_router
from fastapi.middleware.cors import CORSMiddleware
from routers import form_routes
from routers import chat_logger
from routers import admin
from routers import user_info
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
app.include_router(form_routes.router)
app.include_router(admin.router)
app.include_router(user_info.router)
@app.get("/")
def root():
    return {"message": "API is running"}
