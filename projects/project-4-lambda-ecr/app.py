"""
app.py — FastAPI version of the Iris prediction service.

Same functional contract as Project 2's Flask app, but FastAPI-specific:
  - ASGI (vs WSGI) — async-capable, more modern.
  - Pydantic models for input/output validation (vs manual isinstance checks).
  - Auto-generated OpenAPI/Swagger docs served at /docs and /redoc.
  - Type hints drive the validation.

Runs locally via:
    uvicorn app:app --reload --host 127.0.0.1 --port 8000
"""

import pickle
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


MODEL_PATH = Path(__file__).parent / "model.pkl"
CLASS_MAP = {0: "setosa", 1: "versicolor", 2: "virginica"}


class PredictionRequest(BaseModel):
    """Input schema. Pydantic validates incoming JSON against this automatically."""
    features: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Four Iris features: sepal_length, sepal_width, petal_length, petal_width",
        examples=[[5.1, 3.5, 1.4, 0.2]],
    )


class PredictionResponse(BaseModel):
    """Output schema. FastAPI uses this for response validation + /docs rendering."""
    prediction: int
    class_name: str


# Load model at module import time (once per worker process).
# In Lambda/container contexts, "once per cold start."
with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)


app = FastAPI(
    title="Iris Classifier API",
    description="Project 4 — FastAPI on AWS Lambda via Docker + ECR.",
    version="1.0.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Trivial health check for load balancers / probes."""
    return {"status": "healthy"}


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    """
    Classify a single Iris sample. Returns the predicted class index and name.

    pydantic has already validated `request.features` is a 4-element list of
    floats by the time this function runs — no manual checks needed.
    """
    try:
        sample = np.array([request.features], dtype=float)
        class_idx = int(model.predict(sample)[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    return PredictionResponse(
        prediction=class_idx,
        class_name=CLASS_MAP.get(class_idx, "unknown"),
    )