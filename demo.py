#!/usr/bin/env python3
"""
Demo script to test MCP Core functionality.
"""

import asyncio
import json
from mcp_core.mcp_server import get_server
from mcp_core.jobs.job_schema import JobSubmission, JobType
from mcp_core.agents.base_agent import AgentRegistry
from mcp_core.agents.ml_agent import MLAgent
from mcp_core.agents.backtest_agent import BacktestAgent
from mcp_core.utils.logger import setup_logging


async def main():
    """Test MCP Core functionality."""
    # Set up logging
    setup_logging(level="INFO")
    
    # Register agents
    AgentRegistry.register(JobType.ML_EXPERIMENT, MLAgent)
    AgentRegistry.register(JobType.BACKTEST, BacktestAgent)
    
    # Get server instance
    server = get_server()
    
    print("MCP Core Demo")
    print("=" * 50)
    
    # Test 1: Submit ML experiment job
    print("\n1. Submitting ML experiment job...")
    ml_job = JobSubmission(
        type=JobType.ML_EXPERIMENT,
        payload={
            "model": "linear",
            "dataset": "iris",
            "epochs": 5
        },
        metadata={"user": "demo", "priority": "high"}
    )
    
    ml_job_id = await server.submit_job(ml_job)
    print(f"   ML Job ID: {ml_job_id}")
    
    # Test 2: Submit backtest job
    print("\n2. Submitting backtest job...")
    bt_job = JobSubmission(
        type=JobType.BACKTEST,
        payload={
            "strategy": "momentum",
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000
        },
        metadata={"user": "demo", "strategy_version": "v1.0"}
    )
    
    bt_job_id = await server.submit_job(bt_job)
    print(f"   Backtest Job ID: {bt_job_id}")
    
    # Test 3: Monitor job status
    print("\n3. Monitoring job status...")
    
    # Wait for jobs to complete
    while True:
        ml_status = await server.get_job_status(ml_job_id)
        bt_status = await server.get_job_status(bt_job_id)
        
        print(f"   ML Job Status: {ml_status.status}")
        print(f"   Backtest Job Status: {bt_status.status}")
        
        if ml_status.status in ["completed", "failed", "cancelled"] and \
           bt_status.status in ["completed", "failed", "cancelled"]:
            break
        
        await asyncio.sleep(1)
    
    # Test 4: Display results
    print("\n4. Job Results:")
    print("-" * 30)
    
    # ML Job Results
    ml_final = await server.get_job_status(ml_job_id)
    print(f"\nML Experiment Results:")
    print(f"  Status: {ml_final.status}")
    if ml_final.result:
        result = ml_final.result
        print(f"  Model: {result.get('model_type')}")
        print(f"  Dataset: {result.get('dataset')}")
        print(f"  Final Accuracy: {result.get('final_accuracy', 0):.3f}")
        print(f"  Final Loss: {result.get('final_loss', 0):.3f}")
        print(f"  Experiment ID: {result.get('experiment_id')}")
    
    # Backtest Results
    bt_final = await server.get_job_status(bt_job_id)
    print(f"\nBacktest Results:")
    print(f"  Status: {bt_final.status}")
    if bt_final.result:
        result = bt_final.result
        print(f"  Strategy: {result.get('strategy')}")
        print(f"  Ticker: {result.get('ticker')}")
        print(f"  Total Return: {result.get('total_return', 0):.2%}")
        print(f"  Sharpe Ratio: {result.get('sharpe_ratio', 0):.2f}")
        print(f"  Max Drawdown: {result.get('max_drawdown', 0):.2%}")
        print(f"  Number of Trades: {result.get('num_trades')}")
        print(f"  Backtest ID: {result.get('backtest_id')}")
    
    # Test 5: List all jobs
    print("\n5. All Jobs:")
    print("-" * 30)
    all_jobs = await server.list_jobs()
    for job in all_jobs:
        print(f"  {job.id[:8]}... | {job.type} | {job.status} | {job.created_at.strftime('%H:%M:%S')}")
    
    print("\nDemo completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
