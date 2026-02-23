from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Session as SessionModel, Job as JobModel, Result as ResultModel, Reference
from .schemas import (
    SessionCreateResponse, InputCreateRequest, JobCreateResponse,
    JobStatusResponse
)
from .settings import settings
from .worker import process_job

app = FastAPI(title="Voice MVP API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",")] if settings.CORS_ALLOW_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    # default reference 확보
    db = next(get_db())
    try:
        ref = db.query(Reference).filter(Reference.name == "default").first()
        if not ref:
            db.add(Reference(name="default", params_json={"a": 1.0, "b": 0.5, "n_points": 200}))
            db.commit()
    finally:
        db.close()

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/sessions", response_model=SessionCreateResponse)
def create_session(db: Session = Depends(get_db)):
    s = SessionModel()
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"session_id": s.id}

@app.post("/sessions/{session_id}/inputs", response_model=JobCreateResponse)
def create_job(session_id: str, body: InputCreateRequest, bg: BackgroundTasks, db: Session = Depends(get_db)):
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="session not found")

    job = JobModel(
        session_id=session_id,
        status="queued",
        progress=0,
        input_json=body.model_dump()
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # 비동기(간단): 백그라운드에서 모델 호출/DB 저장
    bg.add_task(process_job, job.id)

    return {"job_id": job.id, "status": job.status}

@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {
        "job_id": job.id,
        "session_id": job.session_id,
        "status": job.status,
        "progress": job.progress,
        "error": job.error_text
    }

@app.get("/jobs/{job_id}/result")
def get_result(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    if job.status != "done":
        return {"status": job.status, "progress": job.progress, "error": job.error_text}

    result = db.query(ResultModel).filter(ResultModel.job_id == job.id).first()
    if not result:
        raise HTTPException(status_code=500, detail="result missing")
    return {"status": "done", **result.result_json}
