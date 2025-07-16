from fastapi import FastAPI
from routers.chat import router as chat_router
from fastapi.middleware.cors import CORSMiddleware
from routers import auth_routes as auth_routes
# tablolar (gerekirse) oluştur
Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS (geliştirme için herkes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# ana router
app.include_router(chat_router)
app.include_router(auth_routes.router)
@app.get("/")
def root():
    return {"message": "API is running"}
