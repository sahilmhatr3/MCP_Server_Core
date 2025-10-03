"""
Main MCP Server - Job orchestration and lifecycle management.
"""

import asyncio
import aiohttp
from typing import Dict, Optional, List, Any
from datetime import datetime
import logging

from .jobs.job_schema import Job, JobStatus, JobSubmission, JobResponse
from .agents.base_agent import AgentRegistry
from .artifacts.artifact_registry import ArtifactRegistry
from .utils.logger import get_logger, log_job_event


class MCPServer:
    """Main MCP Server for job orchestration."""
    
    def __init__(self):
        self.logger = get_logger("mcp_server")
        self.jobs: Dict[str, Job] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()
        self.artifact_registry = ArtifactRegistry()
        self._http_session: Optional[aiohttp.ClientSession] = None
        
    async def submit_job(self, job_submission: JobSubmission) -> str:
        """
        Submit a new job for execution.
        
        Args:
            job_submission: Job submission data
            
        Returns:
            Job ID
            
        Raises:
            ValueError: If no agent is available for the job type
        """
        # Create job
        job = Job(
            type=job_submission.type,
            payload=job_submission.payload,
            metadata=job_submission.metadata or {}
        )
        
        # Check if external service is available
        if not AgentRegistry.can_handle_job(job):
            raise ValueError(f"No external service available for job type: {job.type}")
        
        # Store job
        self.jobs[job.id] = job
        
        # Start execution
        task = asyncio.create_task(self._execute_job(job))
        self.running_tasks[job.id] = task
        
        return job.id
    
    async def get_job_status(self, job_id: str) -> Optional[JobResponse]:
        """
        Get the status of a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job response or None if not found
        """
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        return JobResponse(
            id=job.id,
            type=job.type,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            result=job.result,
            error=job.error,
            logs=job.logs,
            metadata=job.metadata
        )
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if job was cancelled, False if not found or already completed
        """
        job = self.jobs.get(job_id)
        if not job:
            return False
        
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False
        
        # Cancel the task
        if job_id in self.running_tasks:
            task = self.running_tasks[job_id]
            task.cancel()
            del self.running_tasks[job_id]
        
        # Update job status
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        
        return True
    
    async def list_jobs(self, status_filter: Optional[JobStatus] = None, limit: Optional[int] = None) -> List[JobResponse]:
        """
        List all jobs, optionally filtered by status.
        
        Args:
            status_filter: Optional status filter
            limit: Maximum number of jobs to return
            
        Returns:
            List of job responses
        """
        jobs = list(self.jobs.values())
        
        if status_filter:
            jobs = [job for job in jobs if job.status == status_filter]
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply limit
        if limit:
            jobs = jobs[:limit]
        
        return [
            JobResponse(
                id=job.id,
                type=job.type,
                status=job.status,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                result=job.result,
                error=job.error,
                logs=job.logs,
                metadata=job.metadata
            )
            for job in jobs
        ]
    
    async def _execute_job(self, job: Job) -> None:
        """
        Execute a job using the appropriate external service.
        
        Args:
            job: Job to execute
        """
        try:
            # Update status to running
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            
            # Get service URL for job type
            service_url = AgentRegistry.get_service_url(job.type)
            if not service_url:
                raise ValueError(f"No service URL configured for job type: {job.type}")
            
            # Execute job via external service
            result = await self._execute_job_via_service(job, service_url)
            
            # Update job with result
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.result = result
            
            # Register any artifacts returned by the service
            await self._register_service_artifacts(job, result)
            
        except asyncio.CancelledError:
            # Job was cancelled
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            raise
            
        except Exception as e:
            # Job failed
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error = str(e)
            self.logger.error(f"Job {job.id} failed: {e}")
            
        finally:
            # Clean up running task
            if job.id in self.running_tasks:
                del self.running_tasks[job.id]
    
    async def _execute_job_via_service(self, job: Job, service_url: str) -> Dict[str, Any]:
        """
        Execute a job via external service HTTP API.
        
        Args:
            job: Job to execute
            service_url: Base URL of the external service
            
        Returns:
            Execution result from the service
        """
        if not self._http_session:
            self._http_session = aiohttp.ClientSession()
        
        # Prepare job data for the service
        job_data = {
            "job_id": job.id,
            "type": job.type,
            "payload": job.payload,
            "metadata": job.metadata
        }
        
        try:
            async with self._http_session.post(
                f"{service_url}/execute",
                json=job_data,
                timeout=aiohttp.ClientTimeout(total=3600)  # 1 hour timeout
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"Service returned status {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to communicate with service {service_url}: {e}")
    
    async def _register_service_artifacts(self, job: Job, result: Dict[str, Any]) -> None:
        """
        Register artifacts returned by the service.
        
        Args:
            job: The completed job
            result: Result from the service
        """
        artifacts = result.get("artifacts", [])
        
        for artifact_data in artifacts:
            try:
                from .artifacts.artifact_schema import ArtifactRegistration
                
                registration = ArtifactRegistration(
                    name=artifact_data.get("name", f"artifact_{job.id}"),
                    type=artifact_data.get("type", "other"),
                    storage_location=artifact_data.get("storage_location", ""),
                    description=artifact_data.get("description"),
                    service_id=artifact_data.get("service_id"),
                    job_id=job.id,
                    dependencies=artifact_data.get("dependencies", []),
                    size_bytes=artifact_data.get("size_bytes"),
                    checksum=artifact_data.get("checksum"),
                    tags=artifact_data.get("tags", []),
                    metadata=artifact_data.get("metadata", {})
                )
                
                await self.artifact_registry.register_artifact(registration)
                
            except Exception as e:
                self.logger.error(f"Failed to register artifact for job {job.id}: {e}")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the server."""
        # Cancel all running tasks
        for task in self.running_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)
        
        # Close HTTP session
        if self._http_session:
            await self._http_session.close()
        
        self._shutdown_event.set()


# Global server instance
_server_instance: Optional[MCPServer] = None


def get_server() -> MCPServer:
    """Get the global server instance."""
    global _server_instance
    if _server_instance is None:
        _server_instance = MCPServer()
    return _server_instance


async def start_server() -> MCPServer:
    """Start the MCP server."""
    server = get_server()
    return server
