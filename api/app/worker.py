import numpy as np
import httpx
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import Job, Result, Reference
from .settings import settings

def _get_default_reference(db: Session) -> Reference:
    ref = db.query(Reference).filter(Reference.name == "default").first()
    if not ref:
        ref = Reference(name="default", params_json={"a": 1.0, "b": 0.5, "n_points": 200})
        db.add(ref)
        db.commit()
        db.refresh(ref)
    return ref

def process_job(job_id: str) -> None:
    """
    BackgroundTasks로 호출됨.
    - jobs.status/progress 업데이트
    - model_service 호출해서 그래프 생성
    - reference와 비교해 score 생성
    - results 저장
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = "running"
        job.progress = 10
        db.commit()

        payload = job.input_json

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{settings.MODEL_URL}/infer", json=payload)
            resp.raise_for_status()
            graph = resp.json()  # {x,y,dy,d2y}

        job.progress = 70
        db.commit()

        ref = _get_default_reference(db)
        a_ref = float(ref.params_json.get("a", 1.0))
        b_ref = float(ref.params_json.get("b", 0.5))

        x = np.array(graph["x"], dtype=float)
        y = np.array(graph["y"], dtype=float)
        ref_y = a_ref * np.sin(x) + b_ref * (x ** 2)

        mse = float(np.mean((y - ref_y) ** 2))
        denom = float(np.mean(ref_y ** 2) + 1e-9)
        rel = min(mse / denom, 1.0)
        score = int(round(100 * (1.0 - rel)))

        summary = {
            "score": score,
            "message": "reference 대비 유사도가 높습니다." if score >= 70 else "reference 대비 차이가 큽니다.",
            "mse": mse,
            "reference": ref.name,
        }

        result_json = {"summary": summary, "graph": graph}

        existing = db.query(Result).filter(Result.job_id == job.id).first()
        if existing:
            existing.result_json = result_json
        else:
            db.add(Result(job_id=job.id, result_json=result_json))

        job.status = "done"
        job.progress = 100
        db.commit()

    except Exception as e:
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.progress = 100
                job.error_text = str(e)
                db.commit()
        finally:
            pass
    finally:
        db.close()
