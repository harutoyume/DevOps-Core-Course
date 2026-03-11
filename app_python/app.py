"""
DevOps Info Service
A web application providing detailed system and runtime information.
"""
import os
import socket
import platform
import logging
import sys
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from pythonjsonlogger import jsonlogger

# Initialize Flask application
app = Flask(__name__)

# Configuration from environment variables
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Application start time for uptime calculation
START_TIME = datetime.now(timezone.utc)

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
        }
    ]


@app.before_request
def log_request():
    """Log incoming HTTP request details."""
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
def log_response(response):
    """Log HTTP response details."""
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
    response = {
        'service': {
            'name': 'devops-info-service',
            'version': '1.0.0',
            'description': 'DevOps course info service',
            'framework': 'Flask'
        },
        'system': get_system_info(),
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
    response = {
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'uptime_seconds': get_uptime()['seconds']
    }
    
    return jsonify(response)


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
