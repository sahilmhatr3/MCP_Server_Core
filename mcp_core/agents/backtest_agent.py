"""
Example Backtest Agent for MCP Core.
"""

import asyncio
import random
from typing import Dict, Any
from datetime import datetime, timedelta

from .base_agent import BaseAgent
from ..jobs.job_schema import Job, JobType


class BacktestAgent(BaseAgent):
    """Example quantitative strategy backtest agent."""
    
    def __init__(self):
        super().__init__()
        self.logger.info("Backtest Agent initialized")
    
    def get_supported_job_types(self) -> list[JobType]:
        """Return supported job types."""
        return [JobType.BACKTEST]
    
    async def execute(self, job: Job) -> Dict[str, Any]:
        """
        Execute a backtest job.
        
        Args:
            job: The job to execute
            
        Returns:
            Backtest results
        """
        self.logger.info(f"Starting backtest for job {job.id}")
        
        # Simulate backtest processing
        await asyncio.sleep(3)  # Simulate processing time
        
        # Extract job parameters
        strategy = job.payload.get("strategy", "momentum")
        ticker = job.payload.get("ticker", "AAPL")
        start_date = job.payload.get("start_date", "2023-01-01")
        end_date = job.payload.get("end_date", "2023-12-31")
        initial_capital = job.payload.get("initial_capital", 100000)
        
        # Simulate backtest results
        total_return = random.uniform(-0.2, 0.4)  # -20% to +40%
        sharpe_ratio = random.uniform(0.5, 2.5)
        max_drawdown = random.uniform(0.05, 0.25)
        
        # Generate trade log
        num_trades = random.randint(10, 50)
        trades = []
        for i in range(num_trades):
            trade_date = datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=random.randint(0, 365))
            trades.append({
                "date": trade_date.strftime("%Y-%m-%d"),
                "action": random.choice(["BUY", "SELL"]),
                "price": random.uniform(100, 200),
                "quantity": random.randint(10, 100),
                "pnl": random.uniform(-1000, 2000)
            })
        
        # Calculate portfolio value over time
        portfolio_values = []
        current_value = initial_capital
        for i in range(252):  # Trading days in a year
            daily_return = random.uniform(-0.05, 0.05)
            current_value *= (1 + daily_return)
            portfolio_values.append({
                "date": (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d"),
                "value": current_value
            })
        
        result = {
            "strategy": strategy,
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
            "final_value": current_value,
            "total_return": total_return,
            "annualized_return": total_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "num_trades": num_trades,
            "trades": trades,
            "portfolio_values": portfolio_values,
            "backtest_id": f"bt_{job.id[:8]}",
            "completed_at": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"Backtest completed for job {job.id}")
        return result
    
    async def validate_job(self, job: Job) -> bool:
        """Validate backtest job parameters."""
        if not await super().validate_job(job):
            return False
        
        # Check required parameters
        required_params = ["strategy", "ticker"]
        for param in required_params:
            if param not in job.payload:
                self.logger.error(f"Missing required parameter: {param}")
                return False
        
        return True
