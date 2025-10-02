"""
Unit tests for MCP Core functionality.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

from mcp_core.jobs.job_schema import Job, JobStatus, JobType, JobSubmission
from mcp_core.agents.base_agent import BaseAgent, AgentRegistry
from mcp_core.mcp_server import MCPServer
from mcp_core.agents.ml_agent import MLAgent
from mcp_core.agents.backtest_agent import BacktestAgent


class TestJobSchema:
    """Test job schema functionality."""
    
    def test_job_creation(self):
        """Test job creation with default values."""
        job = Job(
            type=JobType.ML_EXPERIMENT,
            payload={"model": "linear", "dataset": "iris"}
        )
        
        assert job.type == JobType.ML_EXPERIMENT
        assert job.status == JobStatus.PENDING
        assert job.payload == {"model": "linear", "dataset": "iris"}
        assert job.created_at is not None
        assert job.started_at is None
        assert job.completed_at is None
        assert job.result is None
        assert job.error is None
        assert job.logs == []
        assert job.metadata == {}
    
    def test_job_submission(self):
        """Test job submission model."""
        submission = JobSubmission(
            type=JobType.BACKTEST,
            payload={"strategy": "momentum", "ticker": "AAPL"},
            metadata={"user": "test"}
        )
        
        assert submission.type == JobType.BACKTEST
        assert submission.payload == {"strategy": "momentum", "ticker": "AAPL"}
        assert submission.metadata == {"user": "test"}


class TestAgentRegistry:
    """Test agent registry functionality."""
    
    def setup_method(self):
        """Clear registry before each test."""
        AgentRegistry.clear()
    
    def test_agent_registration(self):
        """Test agent registration."""
        AgentRegistry.register(JobType.ML_EXPERIMENT, MLAgent)
        
        assert JobType.ML_EXPERIMENT in AgentRegistry._agents
        assert AgentRegistry._agents[JobType.ML_EXPERIMENT] == MLAgent
    
    def test_get_agent(self):
        """Test getting agent instance."""
        AgentRegistry.register(JobType.ML_EXPERIMENT, MLAgent)
        
        agent = AgentRegistry.get_agent(JobType.ML_EXPERIMENT)
        assert agent is not None
        assert isinstance(agent, MLAgent)
        
        # Should return same instance on second call
        agent2 = AgentRegistry.get_agent(JobType.ML_EXPERIMENT)
        assert agent is agent2
    
    def test_get_nonexistent_agent(self):
        """Test getting non-existent agent."""
        agent = AgentRegistry.get_agent(JobType.ML_EXPERIMENT)
        assert agent is None
    
    def test_can_handle_job(self):
        """Test job handling capability check."""
        AgentRegistry.register(JobType.ML_EXPERIMENT, MLAgent)
        
        job = Job(type=JobType.ML_EXPERIMENT, payload={})
        assert AgentRegistry.can_handle_job(job) is True
        
        job2 = Job(type=JobType.BACKTEST, payload={})
        assert AgentRegistry.can_handle_job(job2) is False
    
    def test_get_supported_job_types(self):
        """Test getting supported job types."""
        AgentRegistry.register(JobType.ML_EXPERIMENT, MLAgent)
        AgentRegistry.register(JobType.BACKTEST, BacktestAgent)
        
        supported_types = AgentRegistry.get_supported_job_types()
        assert JobType.ML_EXPERIMENT in supported_types
        assert JobType.BACKTEST in supported_types
        assert len(supported_types) == 2


class TestMCPServer:
    """Test MCP server functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        AgentRegistry.clear()
        AgentRegistry.register(JobType.ML_EXPERIMENT, MLAgent)
        self.server = MCPServer()
    
    @pytest.mark.asyncio
    async def test_submit_job(self):
        """Test job submission."""
        job_submission = JobSubmission(
            type=JobType.ML_EXPERIMENT,
            payload={"model": "linear", "dataset": "iris"}
        )
        
        job_id = await self.server.submit_job(job_submission)
        
        assert job_id is not None
        assert job_id in self.server.jobs
        
        job = self.server.jobs[job_id]
        assert job.type == JobType.ML_EXPERIMENT
        assert job.status == JobStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_submit_job_no_agent(self):
        """Test job submission with no available agent."""
        job_submission = JobSubmission(
            type=JobType.BACKTEST,  # No agent registered for this
            payload={"strategy": "momentum"}
        )
        
        with pytest.raises(ValueError, match="No agent available"):
            await self.server.submit_job(job_submission)
    
    @pytest.mark.asyncio
    async def test_get_job_status(self):
        """Test getting job status."""
        job_submission = JobSubmission(
            type=JobType.ML_EXPERIMENT,
            payload={"model": "linear", "dataset": "iris"}
        )
        
        job_id = await self.server.submit_job(job_submission)
        
        # Wait for job to complete
        await asyncio.sleep(3)
        
        job_response = await self.server.get_job_status(job_id)
        
        assert job_response is not None
        assert job_response.id == job_id
        assert job_response.type == JobType.ML_EXPERIMENT
        assert job_response.status in [JobStatus.COMPLETED, JobStatus.RUNNING]
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_job_status(self):
        """Test getting status of non-existent job."""
        job_response = await self.server.get_job_status("nonexistent-id")
        assert job_response is None
    
    @pytest.mark.asyncio
    async def test_cancel_job(self):
        """Test job cancellation."""
        job_submission = JobSubmission(
            type=JobType.ML_EXPERIMENT,
            payload={"model": "linear", "dataset": "iris"}
        )
        
        job_id = await self.server.submit_job(job_submission)
        
        # Cancel immediately
        cancelled = await self.server.cancel_job(job_id)
        
        assert cancelled is True
        
        job = self.server.jobs[job_id]
        assert job.status == JobStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job(self):
        """Test cancelling non-existent job."""
        cancelled = await self.server.cancel_job("nonexistent-id")
        assert cancelled is False
    
    @pytest.mark.asyncio
    async def test_list_jobs(self):
        """Test listing jobs."""
        # Submit multiple jobs
        job1 = JobSubmission(type=JobType.ML_EXPERIMENT, payload={"model": "linear"})
        job2 = JobSubmission(type=JobType.ML_EXPERIMENT, payload={"model": "neural"})
        
        job_id1 = await self.server.submit_job(job1)
        job_id2 = await self.server.submit_job(job2)
        
        # Wait for jobs to complete
        await asyncio.sleep(3)
        
        jobs = await self.server.list_jobs()
        
        assert len(jobs) == 2
        job_ids = [job.id for job in jobs]
        assert job_id1 in job_ids
        assert job_id2 in job_ids
    
    @pytest.mark.asyncio
    async def test_list_jobs_with_filter(self):
        """Test listing jobs with status filter."""
        job_submission = JobSubmission(
            type=JobType.ML_EXPERIMENT,
            payload={"model": "linear", "dataset": "iris"}
        )
        
        job_id = await self.server.submit_job(job_submission)
        
        # List pending jobs
        pending_jobs = await self.server.list_jobs(JobStatus.PENDING)
        assert len(pending_jobs) >= 1
        
        # Wait for completion
        await asyncio.sleep(3)
        
        # List completed jobs
        completed_jobs = await self.server.list_jobs(JobStatus.COMPLETED)
        assert len(completed_jobs) >= 1


class TestMLAgent:
    """Test ML agent functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.agent = MLAgent()
    
    def test_supported_job_types(self):
        """Test supported job types."""
        supported_types = self.agent.get_supported_job_types()
        assert JobType.ML_EXPERIMENT in supported_types
    
    @pytest.mark.asyncio
    async def test_execute_job(self):
        """Test job execution."""
        job = Job(
            type=JobType.ML_EXPERIMENT,
            payload={"model": "linear", "dataset": "iris", "epochs": 3}
        )
        
        result = await self.agent.execute(job)
        
        assert isinstance(result, dict)
        assert "model_type" in result
        assert "dataset" in result
        assert "final_accuracy" in result
        assert "final_loss" in result
        assert "training_history" in result
        assert result["model_type"] == "linear"
        assert result["dataset"] == "iris"
        assert len(result["training_history"]) == 3
    
    @pytest.mark.asyncio
    async def test_validate_job(self):
        """Test job validation."""
        # Valid job
        valid_job = Job(
            type=JobType.ML_EXPERIMENT,
            payload={"model": "linear", "dataset": "iris"}
        )
        assert await self.agent.validate_job(valid_job) is True
        
        # Invalid job type
        invalid_job = Job(
            type=JobType.BACKTEST,
            payload={"strategy": "momentum"}
        )
        assert await self.agent.validate_job(invalid_job) is False
        
        # Missing required parameters
        incomplete_job = Job(
            type=JobType.ML_EXPERIMENT,
            payload={"model": "linear"}  # Missing dataset
        )
        assert await self.agent.validate_job(incomplete_job) is False


class TestBacktestAgent:
    """Test backtest agent functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.agent = BacktestAgent()
    
    def test_supported_job_types(self):
        """Test supported job types."""
        supported_types = self.agent.get_supported_job_types()
        assert JobType.BACKTEST in supported_types
    
    @pytest.mark.asyncio
    async def test_execute_job(self):
        """Test job execution."""
        job = Job(
            type=JobType.BACKTEST,
            payload={
                "strategy": "momentum",
                "ticker": "AAPL",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "initial_capital": 100000
            }
        )
        
        result = await self.agent.execute(job)
        
        assert isinstance(result, dict)
        assert "strategy" in result
        assert "ticker" in result
        assert "total_return" in result
        assert "sharpe_ratio" in result
        assert "max_drawdown" in result
        assert "trades" in result
        assert "portfolio_values" in result
        assert result["strategy"] == "momentum"
        assert result["ticker"] == "AAPL"
    
    @pytest.mark.asyncio
    async def test_validate_job(self):
        """Test job validation."""
        # Valid job
        valid_job = Job(
            type=JobType.BACKTEST,
            payload={"strategy": "momentum", "ticker": "AAPL"}
        )
        assert await self.agent.validate_job(valid_job) is True
        
        # Invalid job type
        invalid_job = Job(
            type=JobType.ML_EXPERIMENT,
            payload={"model": "linear"}
        )
        assert await self.agent.validate_job(invalid_job) is False
        
        # Missing required parameters
        incomplete_job = Job(
            type=JobType.BACKTEST,
            payload={"strategy": "momentum"}  # Missing ticker
        )
        assert await self.agent.validate_job(incomplete_job) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
