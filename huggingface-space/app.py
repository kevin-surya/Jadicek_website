from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from model_service import ModelService

app = FastAPI(title="Jadicek Prediction API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

model = ModelService()


@app.get("/")
@app.get("/health")
def health():
    return {"status": "ready", "model": "notebook-lightgbm"}


@app.post("/api/predict")
def predict(payload: dict):
    try:
        return model.predict(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Prediksi model gagal diproses.") from exc
