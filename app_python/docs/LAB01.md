# Lab 1 - DevOps Info Service: Implementation Report

**Student:** Ilsaf Abdulkhakov  
**Date:** January 27, 2026  
**Lab:** Lab 1 - Web Application Development

---

## 1. Framework Selection

### Chosen Framework: Flask 3.1

I selected **Flask** as the web framework for this project for the following reasons:

1. **Simplicity**: Minimal boilerplate code, ideal for learning web development fundamentals
2. **Lightweight**: Micro-framework providing exactly what we need without unnecessary features
3. **Industry Standard**: Widely used for microservices and REST APIs in DevOps tools
4. **Maturity**: Stable 3.x release with excellent documentation and community support
5. **Perfect Fit**: For a service with 2 endpoints, Flask is neither under-powered nor over-engineered

### Framework Comparison

| Feature | Flask | FastAPI | Django |
|---------|-------|---------|--------|
| **Type** | Micro-framework | Modern async framework | Full-stack framework |
| **Learning Curve** | Easy | Moderate | Steep |
| **Boilerplate** | Minimal | Minimal | Significant |
| **Auto Documentation** | Manual | Automatic (OpenAPI) | Manual |
| **ORM Included** | No | No | Yes (Django ORM) |
| **Use Case** | Microservices, APIs | High-performance APIs | Full web applications |
| **Our Needs** | Perfect fit | Good, but overkill | Too heavy |

**Why not FastAPI?** Automatic documentation and async features aren't necessary for 2 simple endpoints.  
**Why not Django?** Too much overhead (ORM, templates, admin) for a simple REST API.

---

## 2. Best Practices Applied

### Clean Code Organization

Modular functions with single responsibilities:

```python
def get_system_info():
    """Collect comprehensive system information."""
    return {
        'hostname': socket.gethostname(),
        'platform': platform.system(),
        'cpu_count': os.cpu_count(),
        'python_version': platform.python_version()
    }
```

**Importance**: Makes code easier to test, debug, and maintain.

### Documentation

Comprehensive docstrings for all functions:

```python
def get_request_info(req):
    """
    Extract information from the current request.
    
    Args:
        req: Flask request object
    Returns:
        dict: Request information
    """
```

**Importance**: Helps team collaboration and future code maintenance.

### Error Handling

Custom error handlers for graceful error responses:

```python
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested endpoint does not exist',
        'path': request.path
    }), 404
```

**Importance**: Improves user experience and debugging.

### Structured Logging

Consistent logging throughout the application:

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger.info(f"Request: {request.method} {request.path}")
```

**Importance**: Essential for debugging and monitoring production issues.

### Environment-Based Configuration

No hardcoded values, all configurable via environment variables:

```python
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 8080))
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
```

**Importance**: Follows 12-Factor App principles, enables multi-environment deployments.

### PEP 8 Compliance

Code follows Python style guide: 4-space indentation, snake_case naming, descriptive variables.

**Importance**: Ensures code readability and professionalism.

---

## 3. API Documentation

### Endpoint: `GET /`

Returns comprehensive service and system information.

**Request:**
```bash
curl http://localhost:8080/
```

**Response (200 OK):**
```json
{
  "service": {
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course info service",
    "framework": "Flask"
  },
  "system": {
    "hostname": "MacBook-Air-Haru.local",
    "platform": "Darwin",
    "architecture": "arm64",
    "cpu_count": 8,
    "python_version": "3.13.1"
  },
  "runtime": {
    "uptime_seconds": 125,
    "uptime_human": "2 minutes, 5 seconds",
    "current_time": "2026-01-27T13:32:01+00:00",
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
    }
  ]
}
```

### Endpoint: `GET /health`

Health check endpoint for monitoring.

**Request:**
```bash
curl http://localhost:8080/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-27T13:32:05+00:00",
  "uptime_seconds": 20
}
```

### Testing Commands

```bash
# Start application
PORT=8080 python app.py

# Test endpoints
curl http://localhost:8080/
curl http://localhost:8080/health
curl http://localhost:8080/nonexistent  # Test 404

# Pretty print with jq
curl -s http://localhost:8080/ | jq

# Test with different configurations
HOST=127.0.0.1 PORT=3000 python app.py
```

---

## 4. Testing Evidence

### Screenshots

All testing screenshots are in the `screenshots/` directory:

1. **01-main-endpoint.png** - `GET /` endpoint showing complete JSON response
2. **02-health-check.png** - `GET /health` endpoint  
3. **03-formatted-output.png** - Pretty-printed JSON output

### Test Results

✅ Main endpoint returns all required fields (service, system, runtime, request, endpoints)  
✅ Health check returns status, timestamp, and uptime  
✅ Environment variables work (HOST, PORT, DEBUG)  
✅ Error handler returns proper 404 JSON response  
✅ Logging captures all requests  
✅ Code follows PEP 8 style guidelines

### Terminal Output

```bash
# Application startup
$ PORT=8080 python3 app.py
2026-01-27 16:31:44 - INFO - Starting DevOps Info Service on 0.0.0.0:8080
* Running on http://127.0.0.1:8080

# Test main endpoint
$ curl http://localhost:8080/ | python3 -m json.tool
{
  "service": {"name": "devops-info-service", ...},
  "system": {"hostname": "MacBook-Air-Haru.local", ...},
  ...
}

# Test health endpoint  
$ curl http://localhost:8080/health
{"status": "healthy", "timestamp": "2026-01-27T13:32:05Z", "uptime_seconds": 20}
```

---

## 5. Challenges & Solutions

### Challenge 1: Port 5000 Already in Use (macOS)

**Problem**: Default port 5000 conflicted with macOS AirPlay Receiver service.

**Solution**: Used PORT environment variable to run on port 8080 instead:
```bash
PORT=8080 python app.py
```

### Challenge 2: Human-Readable Uptime Formatting

**Problem**: Converting seconds to readable format (e.g., "2 hours, 5 minutes") with proper pluralization.

**Solution**: Implemented conditional logic for different time scales:
```python
if hours > 0:
    human = f"{hours} hour{'s' if hours != 1 else ''}, {minutes} minute{'s' if minutes != 1 else ''}"
elif minutes > 0:
    human = f"{minutes} minute{'s' if minutes != 1 else ''}, {seconds} second{'s' if seconds != 1 else ''}"
else:
    human = f"{seconds} second{'s' if seconds != 1 else ''}"
```

### Challenge 3: Environment Variable Type Conversion

**Problem**: Environment variables are strings, but PORT needs integer and DEBUG needs boolean.

**Solution**: Explicit type conversion with defaults:
```python
PORT = int(os.getenv('PORT', 8080))
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
```

---

## 6. GitHub Community

### Why Starring Repositories Matters

Starring repositories on GitHub serves important purposes:

- **Bookmarking & Discovery**: Creates a curated list of useful projects for future reference
- **Project Validation**: Star counts indicate community trust and help others discover quality projects
- **Maintainer Support**: Shows appreciation for open-source maintainers' work
- **Visibility**: Increases project visibility in GitHub search and recommendations
- **Professional Profile**: Starred repos showcase your interests to potential employers

**For this lab**: Starred the [course repository](https://github.com/Cre-eD/DevOps-Core-Course) and [simple-container-com/api](https://github.com/simple-container-com/api) to support educational resources and DevOps tools.

### Why Following Developers Matters

Following developers creates valuable connections:

- **Learning**: See commits, starred projects, and contributions from experienced developers
- **Stay Updated**: Discover new projects and trends in your technology stack
- **Networking**: Build connections with classmates, professors, and TAs for collaboration
- **Community**: See what others are working on and discover opportunities
- **Career Growth**: Demonstrates engagement with the developer community to employers

**For this lab**: Followed professor [@Cre-eD](https://github.com/Cre-eD), TAs [@marat-biriushev](https://github.com/marat-biriushev) and [@pierrepicaud](https://github.com/pierrepicaud), and classmates to build a learning community.

### GitHub Engagement Best Practices

- Star repositories you genuinely find useful
- Follow developers whose work aligns with your interests
- Engage meaningfully: comment on issues, contribute to discussions
- Build your profile as a portfolio of your professional interests

GitHub is both a code hosting platform and a social network for developers—engaging through stars and follows is essential for professional development.
