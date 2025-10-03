"""
CLI interface for MCP Core.
"""

import asyncio
import json
import sys
from typing import Optional
import click

from ..mcp_server import get_server
from ..jobs.job_schema import JobSubmission, JobType, JobStatus
from ..agents.base_agent import AgentRegistry
from ..utils.logger import setup_logging


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--json-logs', is_flag=True, help='Use JSON log format')
def cli(verbose: bool, json_logs: bool):
    """MCP Core CLI - Job orchestration and management."""
    level = "DEBUG" if verbose else "INFO"
    setup_logging(level=level, json_format=json_logs)


@cli.command()
@click.option('--type', 'job_type', required=True, 
              type=click.Choice(['ml_experiment', 'backtest', 'generic']),
              help='Type of job to submit')
@click.option('--config', required=True, help='Job configuration (JSON string or file path)')
@click.option('--metadata', help='Additional metadata (JSON string)')
def submit(job_type: str, config: str, metadata: Optional[str]):
    """Submit a new job for execution."""
    try:
        # Parse job type
        job_type_enum = JobType(job_type)
        
        # Parse config
        try:
            if config.startswith('{'):
                # JSON string
                payload = json.loads(config)
            else:
                # File path
                with open(config, 'r') as f:
                    payload = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            click.echo(f"Error parsing config: {e}", err=True)
            sys.exit(1)
        
        # Parse metadata
        metadata_dict = None
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError as e:
                click.echo(f"Error parsing metadata: {e}", err=True)
                sys.exit(1)
        
        # Submit job
        async def _submit():
            server = get_server()
            job_submission = JobSubmission(
                type=job_type_enum,
                payload=payload,
                metadata=metadata_dict
            )
            job_id = await server.submit_job(job_submission)
            return job_id
        
        job_id = asyncio.run(_submit())
        click.echo(f"Job submitted successfully: {job_id}")
        
    except Exception as e:
        click.echo(f"Error submitting job: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--job-id', required=True, help='Job ID to check')
def status(job_id: str):
    """Check the status of a job."""
    try:
        async def _status():
            server = get_server()
            job_response = await server.get_job_status(job_id)
            return job_response
        
        job_response = asyncio.run(_status())
        
        if not job_response:
            click.echo(f"Job not found: {job_id}", err=True)
            sys.exit(1)
        
        # Format output
        output = {
            "id": job_response.id,
            "type": job_response.type,
            "status": job_response.status,
            "created_at": job_response.created_at.isoformat(),
            "started_at": job_response.started_at.isoformat() if job_response.started_at else None,
            "completed_at": job_response.completed_at.isoformat() if job_response.completed_at else None,
            "error": job_response.error,
            "logs": job_response.logs
        }
        
        click.echo(json.dumps(output, indent=2))
        
    except Exception as e:
        click.echo(f"Error checking job status: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--job-id', required=True, help='Job ID to cancel')
def cancel(job_id: str):
    """Cancel a running job."""
    try:
        async def _cancel():
            server = get_server()
            return await server.cancel_job(job_id)
        
        cancelled = asyncio.run(_cancel())
        
        if cancelled:
            click.echo(f"Job cancelled: {job_id}")
        else:
            click.echo(f"Job not found or already completed: {job_id}", err=True)
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"Error cancelling job: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--status-filter', 
              type=click.Choice(['pending', 'running', 'completed', 'failed', 'cancelled']),
              help='Filter jobs by status')
def list_jobs(status_filter: Optional[str]):
    """List all jobs."""
    try:
        async def _list():
            server = get_server()
            status_enum = JobStatus(status_filter) if status_filter else None
            return await server.list_jobs(status_enum)
        
        jobs = asyncio.run(_list())
        
        if not jobs:
            click.echo("No jobs found")
            return
        
        # Format output
        output = []
        for job in jobs:
            output.append({
                "id": job.id,
                "type": job.type,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            })
        
        click.echo(json.dumps(output, indent=2))
        
    except Exception as e:
        click.echo(f"Error listing jobs: {e}", err=True)
        sys.exit(1)


@cli.command()
def agents():
    """List registered agents."""
    try:
        supported_types = AgentRegistry.get_supported_job_types()
        
        output = {
            "registered_agents": len(supported_types),
            "supported_job_types": [job_type.value for job_type in supported_types]
        }
        
        click.echo(json.dumps(output, indent=2))
        
    except Exception as e:
        click.echo(f"Error listing agents: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
def serve(host: str, port: int, reload: bool):
    """Start the MCP Orchestrator REST API server."""
    from ..api.server import run_server
    run_server(host=host, port=port, reload=reload)


@cli.command()
@click.option('--job-type', required=True, 
              type=click.Choice(['ml_experiment', 'backtest']),
              help='Job type to register service for')
@click.option('--service-url', required=True, help='Base URL of the external service')
def register_service(job_type: str, service_url: str):
    """Register an external microservice."""
    from ..jobs.job_schema import JobType
    from ..agents.base_agent import AgentRegistry
    
    job_type_enum = JobType(job_type)
    AgentRegistry.register_external_service(job_type_enum, service_url)
    click.echo(f"Registered {job_type} service at {service_url}")


@cli.command()
def list_services():
    """List registered external services."""
    from ..agents.base_agent import AgentRegistry
    
    services = AgentRegistry.get_supported_job_types()
    if not services:
        click.echo("No external services registered")
        return
    
    click.echo("Registered external services:")
    for job_type in services:
        service_url = AgentRegistry.get_service_url(job_type)
        click.echo(f"  {job_type}: {service_url}")


if __name__ == '__main__':
    cli()
