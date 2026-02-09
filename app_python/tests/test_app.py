"""
Unit tests for DevOps Info Service
Tests all endpoints, helper functions, and error handlers.
"""
import pytest
import json
from datetime import datetime, timezone
from app import app, get_system_info, get_uptime, get_runtime_info, get_endpoints


@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_request_context():
    """Create a request context for testing."""
    with app.test_request_context():
        yield


# ============================================================================
# Helper Function Tests
# ============================================================================

@pytest.mark.unit
def test_get_system_info():
    """Test that get_system_info returns expected structure."""
    info = get_system_info()
    
    # Verify all required fields are present
    assert 'hostname' in info
    assert 'platform' in info
    assert 'platform_version' in info
    assert 'architecture' in info
    assert 'cpu_count' in info
    assert 'python_version' in info
    
    # Verify data types
    assert isinstance(info['hostname'], str)
    assert isinstance(info['platform'], str)
    assert isinstance(info['platform_version'], str)
    assert isinstance(info['architecture'], str)
    assert isinstance(info['cpu_count'], int)
    assert isinstance(info['python_version'], str)
    
    # Verify reasonable values
    assert info['cpu_count'] > 0
    assert len(info['hostname']) > 0


@pytest.mark.unit
def test_get_uptime():
    """Test that get_uptime returns expected structure."""
    uptime = get_uptime()
    
    # Verify all required fields are present
    assert 'seconds' in uptime
    assert 'human' in uptime
    
    # Verify data types
    assert isinstance(uptime['seconds'], int)
    assert isinstance(uptime['human'], str)
    
    # Verify reasonable values (app should have been running for at least 0 seconds)
    assert uptime['seconds'] >= 0
    assert len(uptime['human']) > 0


@pytest.mark.unit
def test_get_runtime_info():
    """Test that get_runtime_info returns expected structure."""
    runtime = get_runtime_info()
    
    # Verify all required fields are present
    assert 'uptime_seconds' in runtime
    assert 'uptime_human' in runtime
    assert 'current_time' in runtime
    assert 'timezone' in runtime
    
    # Verify data types
    assert isinstance(runtime['uptime_seconds'], int)
    assert isinstance(runtime['uptime_human'], str)
    assert isinstance(runtime['current_time'], str)
    assert isinstance(runtime['timezone'], str)
    
    # Verify timezone is UTC
    assert runtime['timezone'] == 'UTC'
    
    # Verify current_time is in ISO format
    datetime.fromisoformat(runtime['current_time'])


@pytest.mark.unit
def test_get_endpoints():
    """Test that get_endpoints returns expected structure."""
    endpoints = get_endpoints()
    
    # Verify it returns a list
    assert isinstance(endpoints, list)
    assert len(endpoints) == 2
    
    # Verify each endpoint has required fields
    for endpoint in endpoints:
        assert 'path' in endpoint
        assert 'method' in endpoint
        assert 'description' in endpoint
        assert isinstance(endpoint['path'], str)
        assert isinstance(endpoint['method'], str)
        assert isinstance(endpoint['description'], str)


# ============================================================================
# Endpoint Tests
# ============================================================================

@pytest.mark.integration
def test_index_endpoint_status_code(client):
    """Test that the index endpoint returns 200 OK."""
    response = client.get('/')
    assert response.status_code == 200


@pytest.mark.integration
def test_index_endpoint_content_type(client):
    """Test that the index endpoint returns JSON."""
    response = client.get('/')
    assert response.content_type == 'application/json'


@pytest.mark.integration
def test_index_endpoint_structure(client):
    """Test that the index endpoint returns the expected JSON structure."""
    response = client.get('/')
    data = json.loads(response.data)
    
    # Verify top-level keys
    assert 'service' in data
    assert 'system' in data
    assert 'runtime' in data
    assert 'request' in data
    assert 'endpoints' in data
    
    # Verify service information
    assert 'name' in data['service']
    assert 'version' in data['service']
    assert 'description' in data['service']
    assert 'framework' in data['service']
    assert data['service']['name'] == 'devops-info-service'
    assert data['service']['framework'] == 'Flask'
    
    # Verify system information
    assert 'hostname' in data['system']
    assert 'platform' in data['system']
    assert 'architecture' in data['system']
    assert 'cpu_count' in data['system']
    assert 'python_version' in data['system']
    
    # Verify runtime information
    assert 'uptime_seconds' in data['runtime']
    assert 'uptime_human' in data['runtime']
    assert 'current_time' in data['runtime']
    assert 'timezone' in data['runtime']
    
    # Verify request information
    assert 'client_ip' in data['request']
    assert 'user_agent' in data['request']
    assert 'method' in data['request']
    assert 'path' in data['request']
    assert data['request']['method'] == 'GET'
    assert data['request']['path'] == '/'
    
    # Verify endpoints information
    assert isinstance(data['endpoints'], list)
    assert len(data['endpoints']) == 2


@pytest.mark.integration
def test_health_endpoint_status_code(client):
    """Test that the health endpoint returns 200 OK."""
    response = client.get('/health')
    assert response.status_code == 200


@pytest.mark.integration
def test_health_endpoint_content_type(client):
    """Test that the health endpoint returns JSON."""
    response = client.get('/health')
    assert response.content_type == 'application/json'


@pytest.mark.integration
def test_health_endpoint_structure(client):
    """Test that the health endpoint returns the expected JSON structure."""
    response = client.get('/health')
    data = json.loads(response.data)
    
    # Verify all required fields are present
    assert 'status' in data
    assert 'timestamp' in data
    assert 'uptime_seconds' in data
    
    # Verify values
    assert data['status'] == 'healthy'
    assert isinstance(data['uptime_seconds'], int)
    assert data['uptime_seconds'] >= 0
    
    # Verify timestamp is in ISO format
    datetime.fromisoformat(data['timestamp'])


@pytest.mark.integration
def test_health_endpoint_multiple_calls(client):
    """Test that uptime increases between health checks."""
    import time
    
    # First health check
    response1 = client.get('/health')
    data1 = json.loads(response1.data)
    uptime1 = data1['uptime_seconds']
    
    # Wait a bit
    time.sleep(0.1)
    
    # Second health check
    response2 = client.get('/health')
    data2 = json.loads(response2.data)
    uptime2 = data2['uptime_seconds']
    
    # Uptime should be greater or equal (might be same if too fast)
    assert uptime2 >= uptime1


# ============================================================================
# Error Handler Tests
# ============================================================================

@pytest.mark.integration
def test_404_error_handler(client):
    """Test that 404 errors are handled correctly."""
    response = client.get('/nonexistent')
    assert response.status_code == 404
    
    data = json.loads(response.data)
    assert 'error' in data
    assert 'message' in data
    assert 'path' in data
    assert data['error'] == 'Not Found'
    assert data['path'] == '/nonexistent'


@pytest.mark.integration
def test_404_error_json_response(client):
    """Test that 404 errors return JSON."""
    response = client.get('/this/path/does/not/exist')
    assert response.content_type == 'application/json'


# ============================================================================
# Request Variation Tests
# ============================================================================

@pytest.mark.integration
def test_index_with_custom_user_agent(client):
    """Test that custom user agent is captured."""
    response = client.get('/', headers={'User-Agent': 'TestBot/1.0'})
    data = json.loads(response.data)
    
    assert data['request']['user_agent'] == 'TestBot/1.0'


@pytest.mark.integration
def test_index_captures_client_ip(client):
    """Test that client IP is captured."""
    response = client.get('/')
    data = json.loads(response.data)
    
    # In test environment, this will be 127.0.0.1 or similar
    assert 'client_ip' in data['request']
    assert data['request']['client_ip'] is not None


@pytest.mark.integration
def test_multiple_endpoint_paths(client):
    """Test that different paths are correctly reported."""
    # Test root path
    response1 = client.get('/')
    data1 = json.loads(response1.data)
    assert data1['request']['path'] == '/'
    
    # Test health path
    response2 = client.get('/health')
    data2 = json.loads(response2.data)
    # Health endpoint doesn't include request info, so just verify it works
    assert response2.status_code == 200


# ============================================================================
# Data Type and Validation Tests
# ============================================================================

@pytest.mark.unit
def test_uptime_formatting():
    """Test that uptime human format is reasonable."""
    uptime = get_uptime()
    human = uptime['human']
    
    # Should contain time units
    assert any(unit in human for unit in ['second', 'minute', 'hour'])


@pytest.mark.integration
def test_service_version_format(client):
    """Test that service version follows semantic versioning."""
    response = client.get('/')
    data = json.loads(response.data)
    
    version = data['service']['version']
    # Should match X.Y.Z format
    parts = version.split('.')
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


@pytest.mark.integration
def test_runtime_timezone_is_utc(client):
    """Test that all timestamps are in UTC."""
    response = client.get('/')
    data = json.loads(response.data)
    
    assert data['runtime']['timezone'] == 'UTC'
    
    # Verify timestamp contains timezone info
    timestamp = data['runtime']['current_time']
    assert '+' in timestamp or 'Z' in timestamp
