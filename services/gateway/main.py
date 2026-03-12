from fastapi import FastAPI
from services.gateway.api.routes import router

app = FastAPI()

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}