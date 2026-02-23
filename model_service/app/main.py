from fastapi import FastAPI
from pydantic import BaseModel, Field
import numpy as np

app = FastAPI(title="Dummy Model Service", version="0.1.0")

class InferReq(BaseModel):
    a: float = 1.0
    b: float = 0.5
    n_points: int = Field(default=200, ge=20, le=2000)

@app.post("/infer")
def infer(req: InferReq):
    n = req.n_points
    x = np.linspace(0, 2*np.pi, n, dtype=float)
    y = req.a * np.sin(x) + req.b * (x ** 2)

    dy = np.gradient(y, x)
    d2y = np.gradient(dy, x)

    return {
        "x": x.tolist(),
        "y": y.tolist(),
        "dy": dy.tolist(),
        "d2y": d2y.tolist(),
    }

@app.get("/healthz")
def healthz():
    return {"ok": True}
