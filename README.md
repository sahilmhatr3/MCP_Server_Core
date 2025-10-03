# MCP Orchestrator

A distributed microservices platform for orchestrating machine learning experiments and quantitative trading backtests.

## Architecture

The MCP Orchestrator follows a hub-and-spoke microservices architecture:

- **MCP Orchestrator** - Central coordination hub
- **ML Experiment Microservice** - Machine learning execution engine  
- **Backtest Engine Microservice** - Quantitative trading simulation engine

## Features

- REST API server with FastAPI and OpenAPI documentation
- Central artifact registry with metadata and provenance tracking
- External microservice communication via HTTP APIs
- Job orchestration with status tracking and error handling
- CLI interface for service management
- Workflow chaining through artifact references

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Orchestrator

```bash
python -m mcp_core.api.cli serve
```

### 3. Register External Services

```bash
# Register ML microservice
python -m mcp_core.api.cli register-service --job-type ml_experiment --service-url http://localhost:8001

# Register backtest microservice  
python -m mcp_core.api.cli register-service --job-type backtest --service-url http://localhost:8002
```

### 4. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## API Endpoints

### Jobs
- `POST /jobs` - Submit a new job
- `GET /jobs/{job_id}` - Get job status
- `GET /jobs` - List jobs with filtering
- `DELETE /jobs/{job_id}` - Cancel a job

### Artifacts
- `POST /artifacts` - Register an artifact
- `GET /artifacts/{artifact_id}` - Get artifact details
- `GET /artifacts` - List artifacts with filtering
- `GET /artifacts/job/{job_id}` - Get artifacts by job
- `GET /artifacts/{artifact_id}/dependencies` - Get artifact dependencies

### Health
- `GET /health` - Health check
- `GET /health/ready` - Readiness check

## CLI Commands

```bash
# Start server
python -m mcp_core.api.cli serve [--host HOST] [--port PORT] [--reload]

# Register external service
python -m mcp_core.api.cli register-service --job-type TYPE --service-url URL

# List registered services
python -m mcp_core.api.cli list-services

# Submit job
python -m mcp_core.api.cli submit --type TYPE --config CONFIG [--metadata METADATA]

# Get job status
python -m mcp_core.api.cli status JOB_ID

# List jobs
python -m mcp_core.api.cli list-jobs [--status-filter STATUS]
```

## External Service Integration

External microservices must implement the following API contract:

### Job Execution Endpoint
```
POST /execute
Content-Type: application/json

{
  "job_id": "uuid",
  "type": "ml_experiment|backtest",
  "payload": {...},
  "metadata": {...}
}
```

### Response Format
```json
{
  "status": "completed|failed",
  "result": {...},
  "artifacts": [
    {
      "name": "model.pkl",
      "type": "model",
      "storage_location": "/artifacts/model.pkl",
      "description": "Trained ML model",
      "service_id": "ml-service-1",
      "size_bytes": 1024,
      "checksum": "sha256:...",
      "tags": ["production", "v1.0"],
      "metadata": {...}
    }
  ]
}
```

## Artifact Registry

The central artifact registry tracks:

- Metadata: Name, type, description, creation time
- Storage: Location, size, checksum
- Provenance: Job ID, service ID, dependencies
- Workflow: References and dependencies for chaining

### Artifact Types
- `model` - Trained ML models
- `plot` - Visualizations and charts
- `report` - Analysis reports
- `log` - Execution logs
- `metrics` - Performance metrics
- `data` - Processed datasets
- `config` - Configuration files
- `other` - Miscellaneous artifacts

## Workflow Chaining

Jobs can reference artifacts from previous jobs:

```json
{
  "type": "backtest",
  "payload": {
    "strategy": "ml_signal",
    "model_artifact_id": "artifact-uuid-123",
    "parameters": {...}
  }
}
```

## Project Structure

```
mcp_core/
├── agents/           # External service registry
├── api/              # REST API endpoints and server
├── artifacts/        # Artifact registry system
├── jobs/             # Job schemas and models
├── utils/            # Logging and utilities
└── mcp_server.py     # Main orchestrator server
```

## Development

### Running Tests
```bash
pytest tests/
```

## Next Steps

To complete the distributed platform:

1. **Implement ML Microservice** - Create `ml-experiment-microservice` repo
2. **Implement Backtest Microservice** - Create `backtest-engine-microservice` repo  
3. **Add Cloud Storage** - Google Drive integration for artifacts
4. **Add Authentication** - Service-to-service authentication
5. **Add Persistence** - Database storage for jobs and artifacts
6. **Add Monitoring** - Metrics, logging, and health checks