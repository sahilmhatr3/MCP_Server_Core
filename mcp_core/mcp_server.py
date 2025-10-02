"""
Main MCP Server - Job orchestration and lifecycle management.
"""

import asyncio
from typing import Dict, Optional, List
from datetime import datetime
import logging

from .jobs.job_schema import Job, JobStatus, JobSubmission, JobResponse
from .agents.base_agent import AgentRegistry
from .utils.logger import get_logger, log_job_event


class MCPServer:
    """Main MCP Server for job orchestration."""
    
    def __init__(self):
        self.logger = get_logger("mcp_server")
        self.jobs: Dict[str, Job] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()
        
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
        
        # Check if agent is available
        if not AgentRegistry.can_handle_job(job):
            raise ValueError(f"No agent available for job type: {job.type}")
        
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
    
    async def list_jobs(self, status_filter: Optional[JobStatus] = None) -> List[JobResponse]:
        """
        List all jobs, optionally filtered by status.
        
        Args:
            status_filter: Optional status filter
            
        Returns:
            List of job responses
        """
        jobs = list(self.jobs.values())
        
        if status_filter:
            jobs = [job for job in jobs if job.status == status_filter]
        
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
        Execute a job using the appropriate agent.
        
        Args:
            job: Job to execute
        """
        try:
            # Update status to running
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            
            # Execute job
            result = await AgentRegistry.execute_job(job)
            
            # Update job with result
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.result = result
            
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
            
        finally:
            # Clean up running task
            if job.id in self.running_tasks:
                del self.running_tasks[job.id]
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the server."""
        # Cancel all running tasks
        for task in self.running_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)
        
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
