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
    """Registry for managing agents and routing jobs."""
    
    _agents: Dict[JobType, Type[BaseAgent]] = {}
    _instances: Dict[JobType, BaseAgent] = {}
    
    @classmethod
    def register(cls, job_type: JobType, agent_class: Type[BaseAgent]):
        """
        Register an agent class for a specific job type.
        
        Args:
            job_type: The job type this agent handles
            agent_class: The agent class to register
        """
        cls._agents[job_type] = agent_class
        logger = logging.getLogger("agent_registry")
        logger.info(f"Registered agent {agent_class.__name__} for job type {job_type}")
    
    @classmethod
    def get_agent(cls, job_type: JobType) -> Optional[BaseAgent]:
        """
        Get an agent instance for the given job type.
        
        Args:
            job_type: The job type to get an agent for
            
        Returns:
            Agent instance or None if not found
        """
        if job_type not in cls._agents:
            return None
        
        # Create instance if not exists
        if job_type not in cls._instances:
            agent_class = cls._agents[job_type]
            cls._instances[job_type] = agent_class()
        
        return cls._instances[job_type]
    
    @classmethod
    def get_supported_job_types(cls) -> list[JobType]:
        """
        Get all supported job types.
        
        Returns:
            List of supported job types
        """
        return list(cls._agents.keys())
    
    @classmethod
    def can_handle_job(cls, job: Job) -> bool:
        """
        Check if there's an agent that can handle the given job.
        
        Args:
            job: The job to check
            
        Returns:
            True if an agent can handle the job
        """
        return job.type in cls._agents
    
    @classmethod
    async def execute_job(cls, job: Job) -> Dict[str, Any]:
        """
        Execute a job using the appropriate agent.
        
        Args:
            job: The job to execute
            
        Returns:
            Execution result
            
        Raises:
            ValueError: If no agent is registered for the job type
        """
        agent = cls.get_agent(job.type)
        if not agent:
            raise ValueError(f"No agent registered for job type: {job.type}")
        
        # Validate job
        if not await agent.validate_job(job):
            raise ValueError(f"Agent {agent.__class__.__name__} cannot handle job {job.id}")
        
        # Execute job
        return await agent.execute(job)
    
    @classmethod
    def clear(cls):
        """Clear all registered agents (useful for testing)."""
        cls._agents.clear()
        cls._instances.clear()
