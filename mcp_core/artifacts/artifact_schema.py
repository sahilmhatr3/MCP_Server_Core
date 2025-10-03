"""
Artifact schema definitions for MCP Core.
"""

from enum import Enum
from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class ArtifactType(str, Enum):
    """Types of artifacts that can be produced."""
    MODEL = "model"
    PLOT = "plot"
    REPORT = "report"
    LOG = "log"
    METRICS = "metrics"
    DATA = "data"
    CONFIG = "config"
    OTHER = "other"


class ArtifactMetadata(BaseModel):
    """Metadata for an artifact."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: ArtifactType
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None  # job_id or user_id
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ArtifactReference(BaseModel):
    """Reference to an artifact for workflow chaining."""
    
    artifact_id: str
    artifact_type: ArtifactType
    reference_type: str = "dependency"  # dependency, input, output, etc.
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Artifact(BaseModel):
    """Complete artifact with metadata and storage information."""
    
    metadata: ArtifactMetadata
    storage_location: str  # Path or URL where artifact is stored
    service_id: Optional[str] = None  # Which microservice produced this
    job_id: Optional[str] = None  # Which job produced this
    dependencies: List[ArtifactReference] = Field(default_factory=list)
    referenced_by: List[ArtifactReference] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class ArtifactRegistration(BaseModel):
    """Model for artifact registration requests."""
    
    name: str
    type: ArtifactType
    storage_location: str
    description: Optional[str] = None
    service_id: Optional[str] = None
    job_id: Optional[str] = None
    dependencies: List[ArtifactReference] = Field(default_factory=list)
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ArtifactResponse(BaseModel):
    """Model for artifact responses."""
    
    metadata: ArtifactMetadata
    storage_location: str
    service_id: Optional[str] = None
    job_id: Optional[str] = None
    dependencies: List[ArtifactReference] = []
    referenced_by: List[ArtifactReference] = []
    
    class Config:
        use_enum_values = True
