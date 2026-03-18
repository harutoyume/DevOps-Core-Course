"""
DevOps Info Service
A web application providing detailed system and runtime information.
"""
import os
import socket
import platform
import logging
import sys
import time
from datetime import datetime, timezone
from flask import Flask, jsonify, request, Response, g
from pythonjsonlogger import jsonlogger
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Initialize Flask application
app = Flask(__name__)

# Configuration from environment variables
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Application start time for uptime calculation
START_TIME = datetime.now(timezone.utc)

# =============================================================================
# Prometheus Metrics
# =============================================================================

# Counter: Total HTTP requests (RED method - Rate)
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Histogram: Request duration in seconds (RED method - Duration)
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Gauge: Requests currently being processed
http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently being processed'
)

# Application-specific metrics
devops_info_endpoint_calls = Counter(
    'devops_info_endpoint_calls',
    'Endpoint calls by endpoint name',
    ['endpoint']
)

system_info_collection_duration_seconds = Histogram(
    'system_info_collection_duration_seconds',
    'Time to collect system information',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

# Application info gauge (provides static metadata)
app_info = Gauge(
    'devops_info_service_info',
    'Application information',
    ['version', 'python_version']
)
app_info.labels(version='1.0.0', python_version=platform.python_version()).set(1)

# Configure JSON logging for structured log output
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that adds standard fields to every log entry."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name


def setup_logging():
    """Set up JSON-formatted logging to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)


setup_logging()
logger = logging.getLogger(__name__)


def get_system_info():
    """
    Collect comprehensive system information.
    
    Returns:
        dict: System information including hostname, platform, architecture, etc.
    """
    return {
        'hostname': socket.gethostname(),
        'platform': platform.system(),
        'platform_version': platform.version(),
        'architecture': platform.machine(),
        'cpu_count': os.cpu_count(),
        'python_version': platform.python_version()
    }


def get_uptime():
    """
    Calculate application uptime.
    
    Returns:
        dict: Uptime in seconds and human-readable format.
    """
    delta = datetime.now(timezone.utc) - START_TIME
    total_seconds = int(delta.total_seconds())
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    # Format human-readable uptime
    if hours > 0:
        human = f"{hours} hour{'s' if hours != 1 else ''}, {minutes} minute{'s' if minutes != 1 else ''}"
    elif minutes > 0:
        human = f"{minutes} minute{'s' if minutes != 1 else ''}, {seconds} second{'s' if seconds != 1 else ''}"
    else:
        human = f"{seconds} second{'s' if seconds != 1 else ''}"
    
    return {
        'seconds': total_seconds,
        'human': human
    }


def get_runtime_info():
    """
    Get current runtime information.
    
    Returns:
        dict: Runtime information including uptime and current time.
    """
    uptime = get_uptime()
    return {
        'uptime_seconds': uptime['seconds'],
        'uptime_human': uptime['human'],
        'current_time': datetime.now(timezone.utc).isoformat(),
        'timezone': 'UTC'
    }


def get_request_info(req):
    """
    Extract information from the current request.
    
    Args:
        req: Flask request object
        
    Returns:
        dict: Request information including client IP, user agent, etc.
    """
    return {
        'client_ip': req.remote_addr,
        'user_agent': req.headers.get('User-Agent', 'Unknown'),
        'method': req.method,
        'path': req.path
    }


def get_endpoints():
    """
    List all available API endpoints.
    
    Returns:
        list: List of endpoint information dictionaries.
    """
    return [
        {
            'path': '/',
            'method': 'GET',
            'description': 'Service information'
        },
        {
            'path': '/health',
            'method': 'GET',
            'description': 'Health check'
        },
        {
            'path': '/metrics',
            'method': 'GET',
            'description': 'Prometheus metrics'
        }
    ]


def normalize_endpoint(path):
    """
    Normalize endpoint path for metric labels.
    Keeps cardinality low by grouping similar paths.
    
    Args:
        path: The request path
        
    Returns:
        str: Normalized endpoint name
    """
    if path == '/':
        return '/'
    elif path == '/health':
        return '/health'
    elif path == '/metrics':
        return '/metrics'
    else:
        return '/other'


@app.before_request
def before_request_metrics():
    """Track request start time and increment in-progress gauge."""
    # Skip metrics endpoint to avoid self-referential metrics
    if request.path == '/metrics':
        return
    
    g.start_time = time.time()
    http_requests_in_progress.inc()


@app.before_request
def log_request():
    """Log incoming HTTP request details."""
    # Skip logging for metrics endpoint
    if request.path == '/metrics':
        return
    
    logger.info(
        "Incoming request",
        extra={
            'method': request.method,
            'path': request.path,
            'client_ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        }
    )


@app.after_request
def after_request_metrics(response):
    """Record request metrics after completion."""
    # Skip metrics endpoint
    if request.path == '/metrics':
        return response
    
    # Calculate request duration
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        endpoint = normalize_endpoint(request.path)
        
        # Record histogram observation
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)
        
        # Increment request counter
        http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status=str(response.status_code)
        ).inc()
        
        # Decrement in-progress gauge
        http_requests_in_progress.dec()
    
    return response


@app.after_request
def log_response(response):
    """Log HTTP response details."""
    # Skip logging for metrics endpoint
    if request.path == '/metrics':
        return response
    
    logger.info(
        "Request completed",
        extra={
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'client_ip': request.remote_addr
        }
    )
    return response


@app.route('/')
def index():
    """
    Main endpoint - returns comprehensive service and system information.
    
    Returns:
        JSON response with service, system, runtime, request info, and endpoints.
    """
    # Track business metric
    devops_info_endpoint_calls.labels(endpoint='/').inc()
    
    # Track system info collection time
    with system_info_collection_duration_seconds.time():
        system_info = get_system_info()
    
    response = {
        'service': {
            'name': 'devops-info-service',
            'version': '1.0.0',
            'description': 'DevOps course info service',
            'framework': 'Flask'
        },
        'system': system_info,
        'runtime': get_runtime_info(),
        'request': get_request_info(request),
        'endpoints': get_endpoints()
    }
    
    return jsonify(response)


@app.route('/health')
def health():
    """
    Health check endpoint for monitoring and Kubernetes probes.
    
    Returns:
        JSON response with health status and uptime.
    """
    # Track business metric
    devops_info_endpoint_calls.labels(endpoint='/health').inc()
    
    response = {
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'uptime_seconds': get_uptime()['seconds']
    }
    
    return jsonify(response)


@app.route('/metrics')
def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns:
        Prometheus text format metrics.
    """
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.errorhandler(404)
def not_found(error):
    """
    Handle 404 errors.
    
    Args:
        error: The error object
        
    Returns:
        JSON error response with 404 status code.
    """
    logger.warning("404 Not Found", extra={'path': request.path})
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested endpoint does not exist',
        'path': request.path
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """
    Handle 500 errors.
    
    Args:
        error: The error object
        
    Returns:
        JSON error response with 500 status code.
    """
    logger.error("500 Internal Server Error", extra={'error': str(error)})
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred'
    }), 500


if __name__ == '__main__':
    logger.info(
        'Starting DevOps Info Service',
        extra={'host': HOST, 'port': PORT, 'debug': DEBUG}
    )
    app.run(host=HOST, port=PORT, debug=DEBUG)
