from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class SessionCreateResponse(BaseModel):
    session_id: str

class InputCreateRequest(BaseModel):
    a: float = 1.0
    b: float = 0.5
    n_points: int = Field(default=200, ge=20, le=2000)

class JobCreateResponse(BaseModel):
    job_id: str
    status: str

class JobStatusResponse(BaseModel):
    job_id: str
    session_id: str
    status: str
    progress: int
    error: Optional[str] = None

class ResultResponse(BaseModel):
    status: str
    summary: Dict[str, Any]
    graph: Dict[str, List[float]]
