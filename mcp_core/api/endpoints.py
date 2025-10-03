"""
REST API endpoints for MCP Core.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import logging

from ..jobs.job_schema import JobSubmission, JobResponse, JobStatus, JobType
from ..artifacts.artifact_schema import ArtifactRegistration, ArtifactResponse, ArtifactType
from ..mcp_server import get_server
from ..artifacts.artifact_registry import ArtifactRegistry

logger = logging.getLogger("api")

# Create routers
jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])
artifacts_router = APIRouter(prefix="/artifacts", tags=["artifacts"])
health_router = APIRouter(prefix="/health", tags=["health"])


# Dependency to get MCP server instance
def get_mcp_server():
    return get_server()


# Dependency to get artifact registry instance
def get_artifact_registry(server = Depends(get_mcp_server)):
    return server.artifact_registry


# Health endpoints
@health_router.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mcp-orchestrator"}


@health_router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {"status": "ready", "service": "mcp-orchestrator"}


# Job endpoints
@jobs_router.post("/", response_model=dict)
async def submit_job(
    job_submission: JobSubmission,
    server = Depends(get_mcp_server)
):
    """
    Submit a new job for execution.
    
    Args:
        job_submission: Job submission data
        
    Returns:
        Job ID and status
    """
    try:
        job_id = await server.submit_job(job_submission)
        return {"job_id": job_id, "status": "submitted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting job: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@jobs_router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    server = Depends(get_mcp_server)
):
    """
    Get the status of a job.
    
    Args:
        job_id: The job ID
        
    Returns:
        Job status and details
    """
    job_response = await server.get_job_status(job_id)
    if not job_response:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_response


@jobs_router.get("/", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    limit: Optional[int] = Query(100, description="Maximum number of jobs to return"),
    server = Depends(get_mcp_server)
):
    """
    List jobs with optional filtering.
    
    Args:
        status: Optional status filter
        limit: Maximum number of jobs to return
        
    Returns:
        List of jobs
    """
    jobs = await server.list_jobs(status_filter=status, limit=limit)
    return jobs


@jobs_router.delete("/{job_id}")
async def cancel_job(
    job_id: str,
    server = Depends(get_mcp_server)
):
    """
    Cancel a running job.
    
    Args:
        job_id: The job ID
        
    Returns:
        Cancellation status
    """
    success = await server.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    return {"job_id": job_id, "status": "cancelled"}


# Artifact endpoints
@artifacts_router.post("/", response_model=dict)
async def register_artifact(
    artifact_registration: ArtifactRegistration,
    registry = Depends(get_artifact_registry)
):
    """
    Register a new artifact.
    
    Args:
        artifact_registration: Artifact registration data
        
    Returns:
        Artifact ID
    """
    try:
        artifact_id = await registry.register_artifact(artifact_registration)
        return {"artifact_id": artifact_id, "status": "registered"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error registering artifact: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@artifacts_router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: str,
    registry = Depends(get_artifact_registry)
):
    """
    Get an artifact by ID.
    
    Args:
        artifact_id: The artifact ID
        
    Returns:
        Artifact details
    """
    artifact = await registry.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    return ArtifactResponse(
        metadata=artifact.metadata,
        storage_location=artifact.storage_location,
        service_id=artifact.service_id,
        job_id=artifact.job_id,
        dependencies=artifact.dependencies,
        referenced_by=artifact.referenced_by
    )


@artifacts_router.get("/", response_model=List[ArtifactResponse])
async def list_artifacts(
    artifact_type: Optional[ArtifactType] = Query(None, description="Filter by artifact type"),
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    service_id: Optional[str] = Query(None, description="Filter by service ID"),
    limit: Optional[int] = Query(100, description="Maximum number of artifacts to return"),
    registry = Depends(get_artifact_registry)
):
    """
    List artifacts with optional filtering.
    
    Args:
        artifact_type: Optional type filter
        job_id: Optional job ID filter
        service_id: Optional service ID filter
        limit: Maximum number of artifacts to return
        
    Returns:
        List of artifacts
    """
    artifacts = await registry.list_artifacts(
        artifact_type=artifact_type,
        job_id=job_id,
        service_id=service_id,
        limit=limit
    )
    
    return [
        ArtifactResponse(
            metadata=artifact.metadata,
            storage_location=artifact.storage_location,
            service_id=artifact.service_id,
            job_id=artifact.job_id,
            dependencies=artifact.dependencies,
            referenced_by=artifact.referenced_by
        )
        for artifact in artifacts
    ]


@artifacts_router.get("/job/{job_id}", response_model=List[ArtifactResponse])
async def get_artifacts_by_job(
    job_id: str,
    registry = Depends(get_artifact_registry)
):
    """
    Get all artifacts produced by a specific job.
    
    Args:
        job_id: The job ID
        
    Returns:
        List of artifacts
    """
    artifacts = await registry.get_artifacts_by_job(job_id)
    
    return [
        ArtifactResponse(
            metadata=artifact.metadata,
            storage_location=artifact.storage_location,
            service_id=artifact.service_id,
            job_id=artifact.job_id,
            dependencies=artifact.dependencies,
            referenced_by=artifact.referenced_by
        )
        for artifact in artifacts
    ]


@artifacts_router.get("/{artifact_id}/dependencies", response_model=List[ArtifactResponse])
async def get_artifact_dependencies(
    artifact_id: str,
    registry = Depends(get_artifact_registry)
):
    """
    Get all artifacts that the given artifact depends on.
    
    Args:
        artifact_id: The artifact ID
        
    Returns:
        List of dependency artifacts
    """
    artifacts = await registry.get_artifact_dependencies(artifact_id)
    
    return [
        ArtifactResponse(
            metadata=artifact.metadata,
            storage_location=artifact.storage_location,
            service_id=artifact.service_id,
            job_id=artifact.job_id,
            dependencies=artifact.dependencies,
            referenced_by=artifact.referenced_by
        )
        for artifact in artifacts
    ]


@artifacts_router.delete("/{artifact_id}")
async def delete_artifact(
    artifact_id: str,
    registry = Depends(get_artifact_registry)
):
    """
    Delete an artifact from the registry.
    
    Args:
        artifact_id: The artifact ID
        
    Returns:
        Deletion status
    """
    success = await registry.delete_artifact(artifact_id)
    if not success:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"artifact_id": artifact_id, "status": "deleted"}
