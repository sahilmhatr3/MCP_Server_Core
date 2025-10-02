"""
Job schema definitions and status enums for MCP Core.
"""

from enum import Enum
from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Supported job types."""
    ML_EXPERIMENT = "ml_experiment"
    BACKTEST = "backtest"
    GENERIC = "generic"


class Job(BaseModel):
    """Job model representing a task to be executed."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: JobType
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class JobSubmission(BaseModel):
    """Model for job submission requests."""
    
    type: JobType
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class JobResponse(BaseModel):
    """Model for job status/results responses."""
    
    id: str
    type: JobType
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: List[str] = []
    metadata: Dict[str, Any] = {}
    
    class Config:
        use_enum_values = True
