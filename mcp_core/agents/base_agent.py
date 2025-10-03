"""
Abstract base agent class and registry system for MCP Core.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
import asyncio
import logging
from datetime import datetime

from ..jobs.job_schema import Job, JobStatus, JobType


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"agent.{self.__class__.__name__}")
    
    @abstractmethod
    async def execute(self, job: Job) -> Dict[str, Any]:
        """
        Execute a job and return the result.
        
        Args:
            job: The job to execute
            
        Returns:
            Dict containing the execution result
        """
        pass
    
    @abstractmethod
    def get_supported_job_types(self) -> list[JobType]:
        """
        Return the job types this agent can handle.
        
        Returns:
            List of supported JobType enums
        """
        pass
    
    async def validate_job(self, job: Job) -> bool:
        """
        Validate that this agent can handle the given job.
        Override in subclasses for custom validation.
        
        Args:
            job: The job to validate
            
        Returns:
            True if the job is valid for this agent
        """
        return job.type in self.get_supported_job_types()


class AgentRegistry:
    """Registry for managing external microservices and routing jobs."""
    
    _external_services: Dict[JobType, str] = {}  # job_type -> service_url
    
    @classmethod
    def register_external_service(cls, job_type: JobType, service_url: str):
        """
        Register an external microservice for a specific job type.
        
        Args:
            job_type: The job type this service handles
            service_url: The base URL of the external service
        """
        cls._external_services[job_type] = service_url
        logging.getLogger("agent_registry").info(f"Registered external service {service_url} for job type {job_type}")
    
    @classmethod
    def get_service_url(cls, job_type: JobType) -> Optional[str]:
        """
        Get the service URL for the given job type.
        
        Args:
            job_type: The job type to get service URL for
            
        Returns:
            Service URL or None if not found
        """
        return cls._external_services.get(job_type)
    
    @classmethod
    def get_supported_job_types(cls) -> list[JobType]:
        """
        Get all supported job types.
        
        Returns:
            List of supported job types
        """
        return list(cls._external_services.keys())
    
    @classmethod
    def can_handle_job(cls, job: Job) -> bool:
        """
        Check if there's a service that can handle the given job.
        
        Args:
            job: The job to check
            
        Returns:
            True if a service can handle the job
        """
        return job.type in cls._external_services
    
    @classmethod
    def clear(cls):
        """Clear all registered services (useful for testing)."""
        cls._external_services.clear()
