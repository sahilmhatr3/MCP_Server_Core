"""
Example ML Agent for MCP Core.
"""

import asyncio
import random
from typing import Dict, Any
from datetime import datetime

from .base_agent import BaseAgent
from ..jobs.job_schema import Job, JobType


class MLAgent(BaseAgent):
    """Example ML experiment agent."""
    
    def __init__(self):
        super().__init__()
        self.logger.info("ML Agent initialized")
    
    def get_supported_job_types(self) -> list[JobType]:
        """Return supported job types."""
        return [JobType.ML_EXPERIMENT]
    
    async def execute(self, job: Job) -> Dict[str, Any]:
        """
        Execute an ML experiment job.
        
        Args:
            job: The job to execute
            
        Returns:
            Experiment results
        """
        self.logger.info(f"Starting ML experiment for job {job.id}")
        
        # Simulate ML experiment
        await asyncio.sleep(2)  # Simulate processing time
        
        # Extract job parameters
        model_type = job.payload.get("model", "linear")
        dataset = job.payload.get("dataset", "iris")
        epochs = job.payload.get("epochs", 10)
        
        # Simulate training metrics
        accuracy = random.uniform(0.7, 0.95)
        loss = random.uniform(0.1, 0.5)
        
        # Generate training history
        training_history = []
        for epoch in range(epochs):
            training_history.append({
                "epoch": epoch + 1,
                "loss": loss * (1 - epoch / epochs) + random.uniform(-0.1, 0.1),
                "accuracy": accuracy * (epoch / epochs) + random.uniform(-0.05, 0.05)
            })
        
        result = {
            "model_type": model_type,
            "dataset": dataset,
            "epochs": epochs,
            "final_accuracy": accuracy,
            "final_loss": loss,
            "training_history": training_history,
            "experiment_id": f"exp_{job.id[:8]}",
            "completed_at": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"ML experiment completed for job {job.id}")
        return result
    
    async def validate_job(self, job: Job) -> bool:
        """Validate ML job parameters."""
        if not await super().validate_job(job):
            return False
        
        # Check required parameters
        required_params = ["model", "dataset"]
        for param in required_params:
            if param not in job.payload:
                self.logger.error(f"Missing required parameter: {param}")
                return False
        
        return True
