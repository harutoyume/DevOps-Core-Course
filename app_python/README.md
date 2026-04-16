[![CI/CD Pipeline](https://github.com/harutoyume/DevOps-Core-Course/actions/workflows/python-ci.yml/badge.svg)](https://github.com/harutoyume/DevOps-Core-Course/actions/workflows/python-ci.yml)

# DevOps Info Service

A lightweight Python web service that provides comprehensive system and runtime information through a REST API. Built with Flask as part of the DevOps Engineering course.

## Overview

The DevOps Info Service is designed to report detailed information about itself and its runtime environment. This service will evolve throughout the course, with additional features like containerization, CI/CD pipelines, monitoring, and persistence being added in future labs.

**Current Features:**
- System information introspection (hostname, platform, architecture, CPU count, Python version)
- Runtime metrics (uptime tracking, current time)
- Request details (client IP, user agent, HTTP method, path)
- **Visit counter with persistent storage** (tracks page visits across container restarts)
- Health check endpoint for monitoring
- **Prometheus metrics endpoint** for observability
- Configurable via environment variables
- JSON API responses
- Error handling and logging
- Automated CI/CD pipeline with GitHub Actions
- Comprehensive test suite with pytest
- Security scanning with Snyk

## Prerequisites

- **Python 3.11+** (tested with Python 3.13)
- **pip** (Python package manager)
- **Virtual environment** (recommended)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/harutoyume/DevOps-Core-Course.git
   cd DevOps-Core-Course/app_python
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate on macOS/Linux
   source venv/bin/activate
   
   # Activate on Windows
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Basic Usage

Run with default settings (host: 0.0.0.0, port: 5000):

```bash
python app.py
```

The service will be accessible at `http://localhost:5000`

### Custom Configuration

Use environment variables to customize the service:

```bash
# Run on a different port
PORT=8080 python app.py

# Run on localhost only
HOST=127.0.0.1 python app.py

# Enable debug mode (for development only)
DEBUG=true python app.py

# Combine multiple configurations
HOST=127.0.0.1 PORT=3000 DEBUG=true python app.py
```

## Docker

This application is containerized and available on Docker Hub. You can run it using Docker without installing Python or dependencies locally.

### Pull from Docker Hub

Pull the pre-built image from Docker Hub:

```bash
docker pull haruyume/devops-info-service:latest
```

Or pull a specific version:

```bash
docker pull haruyume/devops-info-service:1.0.0
```

### Run the Container

Run the container with default settings (port 5001 on host, mapping to 5000 in container):

```bash
docker run -p 5001:5000 haruyume/devops-info-service:latest
```

Run in detached mode (background):

```bash
docker run -d -p 5001:5000 --name devops-service haruyume/devops-info-service:latest
```

Run with custom configuration using environment variables:

```bash
docker run -p 8081:8080 -e PORT=8080 -e DEBUG=true haruyume/devops-info-service:latest
```

Run with persistent data volume for visit counter:

```bash
docker run -d -p 5001:5000 -v $(pwd)/data:/data --name devops-service haruyume/devops-info-service:latest
```

### Docker Compose

The easiest way to run the application with persistent storage is using Docker Compose.

**Start the service:**

```bash
docker-compose up -d
```

**View logs:**

```bash
docker-compose logs -f
```

**Stop the service:**

```bash
docker-compose down
```

**Rebuild and restart:**

```bash
docker-compose up -d --build
```

The `docker-compose.yml` configuration includes:
- Automatic container restart policy
- Volume mounting for visit counter persistence (`./data:/data`)
- Health checks
- Environment variable configuration

### Build Locally

If you want to build the image yourself:

```bash
# Build from the app_python directory
docker build -t devops-info-service:latest .

# Or build from the repository root
docker build -t devops-info-service:latest app_python/
```

### Docker Commands Reference

```bash
# View running containers
docker ps

# View container logs
docker logs <container-name>

# Stop a running container
docker stop <container-name>

# Remove a stopped container
docker rm <container-name>

# View image details
docker inspect haruyume/devops-info-service:latest

# Remove local image
docker rmi haruyume/devops-info-service:latest
```

### Docker Image Details

- **Base Image:** python:3.13-slim
- **Size:** ~150-200MB
- **Security:** Runs as non-root user
- **Internal Port:** 5000
- **Recommended Host Port:** 5001 (to avoid macOS AirPlay conflict)
- **Docker Hub:** [haruyume/devops-info-service](https://hub.docker.com/r/haruyume/devops-info-service)

## API Endpoints

### `GET /`

Returns comprehensive service and system information.

**Request:**
```bash
curl http://localhost:5000/
```

**Response:** (200 OK)
```json
{
  "service": {
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course info service",
    "framework": "Flask"
  },
  "system": {
    "hostname": "my-laptop",
    "platform": "Darwin",
    "platform_version": "Darwin Kernel Version 25.2.0",
    "architecture": "arm64",
    "cpu_count": 8,
    "python_version": "3.13.1"
  },
  "runtime": {
    "uptime_seconds": 3600,
    "uptime_human": "1 hour, 0 minutes",
    "current_time": "2026-01-27T14:30:00.000000+00:00",
    "timezone": "UTC"
  },
  "request": {
    "client_ip": "127.0.0.1",
    "user_agent": "curl/8.7.1",
    "method": "GET",
    "path": "/"
  },
  "endpoints": [
    {
      "path": "/",
      "method": "GET",
      "description": "Service information"
    },
    {
      "path": "/health",
      "method": "GET",
      "description": "Health check"
    },
    {
      "path": "/visits",
      "method": "GET",
      "description": "Visit counter"
    },
    {
      "path": "/metrics",
      "method": "GET",
      "description": "Prometheus metrics"
    }
  ],
  "visits": 42
}
```

**Note:** The response now includes a `visits` field showing the total number of times the root endpoint has been accessed.

### `GET /health`

Health check endpoint for monitoring and Kubernetes probes.

**Request:**
```bash
curl http://localhost:5000/health
```

**Response:** (200 OK)
```json
{
  "status": "healthy",
  "timestamp": "2026-01-27T14:30:00.000000+00:00",
  "uptime_seconds": 3600
}
```

### `GET /visits`

Returns the current visit counter value.

**Request:**
```bash
curl http://localhost:5000/visits
```

**Response:** (200 OK)
```json
{
  "visits": 42,
  "timestamp": "2026-01-27T14:30:00.000000+00:00"
}
```

**Note:** The visit counter increments each time the root endpoint (`/`) is accessed. The counter persists across container restarts when using volume mounting.

### `GET /metrics`

Prometheus metrics endpoint for monitoring and observability.

**Request:**
| `DATA_DIR` | `/data` | Directory path for persistent data storage (visits counter) |
```bash
curl http://localhost:5000/metrics
```

**Response:** (200 OK, text/plain)
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/",method="GET",status="200"} 42.0
# ... more metrics
```

### Error Responses

**404 Not Found:**
```bash
curl http://localhost:5000/nonexistent
```

```json
{
  "error": "Not Found",
  "message": "The requested endpoint does not exist",
  "path": "/nonexistent"
}
```

## Configuration

The application supports the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Host address to bind to (use `127.0.0.1` for localhost only) |
| `PORT` | `5000` | Port number to listen on |
| `DEBUG` | `False` | Enable Flask debug mode (`true` or `false`) |

## Testing

This application includes a comprehensive test suite with 23+ tests covering all endpoints, helper functions, and error handlers.

### Running Tests Locally

1. **Install test dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Run all tests**:
   ```bash
   pytest -v
   ```

3. **Run specific test categories**:
   ```bash
   # Run only unit tests
   pytest -m unit -v
   
   # Run only integration tests
   pytest -m integration -v
   ```

4. **Run linter**:
   ```bash
   ruff check .
   ```

### Test Coverage

The test suite covers:
- All API endpoints (`/`, `/health`)
- Helper functions (`get_system_info`, `get_uptime`, `get_runtime_info`)
- Error handlers (404, 500)
- JSON structure validation
- Request metadata capture
- Edge cases and error conditions

### Continuous Integration

Every push and pull request automatically triggers:
- **Linting** with Ruff (Python style and syntax checking)
- **Unit tests** with pytest (23+ tests)
- **Security scanning** with Snyk (vulnerability detection)
- **Docker build** with CalVer versioning (on master/lab03 branches)

View the CI/CD pipeline: [GitHub Actions](https://github.com/harutoyume/DevOps-Core-Course/actions)

## Manual Testing

### Using curl

Test the main endpoint:
```bash
curl http://localhost:5000/
```

Test the health check:
```bash
curl http://localhost:5000/health
```

Pretty-print JSON output (requires `jq`):
```bash
curl http://localhost:5000/ | jq
```

### Using HTTPie

If you have [HTTPie](https://httpie.io/) installed:
```bash
http http://localhost:5000/
http http://localhost:5000/health
```

### Using a Web Browser

Simply navigate to:
- `http://localhost:5000/` - Main endpoint
- `http://localhost:5000/health` - Health check

### Using Postman

1. Create a new GET request to `http://localhost:5000/`
2. Send the request
3. View the formatted JSON response

## Development

### Code Structure

- `app.py` - Main application with Flask routes and helper functions
- `requirements.txt` - Python dependencies
- `.gitignore` - Files and directories to exclude from version control
- `tests/` - Unit tests (to be added in Lab 3)
- `docs/` - Lab documentation and screenshots

### Best Practices Implemented

- **Clean Code**: Well-organized functions with single responsibilities
- **Documentation**: Comprehensive docstrings for all functions
- **Error Handling**: Custom error handlers for 404 and 500 errors
- **Logging**: Structured logging for debugging and monitoring
- **Configuration**: Environment-based configuration
- **PEP 8 Compliance**: Follows Python style guidelines

## Logging

The application logs important events to stdout:

- Application startup information
- Request processing (info level)
- Health check requests (debug level)
- Errors and warnings

Example log output:
```
2026-01-27 14:30:00,000 - __main__ - INFO - Starting DevOps Info Service on 0.0.0.0:5000
2026-01-27 14:30:00,001 - __main__ - INFO - Debug mode: False
2026-01-27 14:30:15,123 - __main__ - INFO - Request: GET / from 127.0.0.1
```

## Future Enhancements

This service will be extended in future labs:

- **Lab 2**: Docker containerization with multi-stage builds
- **Lab 3**: Unit tests and CI/CD pipeline with GitHub Actions
- **Lab 8**: Prometheus `/metrics` endpoint
- **Lab 9**: Kubernetes deployment with health probes
- **Lab 12**: Visit counter with file persistence
- **Lab 13**: Multi-environment deployment with GitOps

## Troubleshooting

**Port already in use:**
```bash
# Use a different port
PORT=8080 python app.py
```

**Module not found error:**
```bash
# Make sure virtual environment is activated and dependencies are installed
source venv/bin/activate
pip install -r requirements.txt
```

**Permission denied:**
```bash
# Don't use privileged ports (< 1024) or run with appropriate permissions
PORT=5000 python app.py
```

## License

This project is part of the DevOps Engineering course.

## Author

Created as part of Lab 1 - Web Application Development
