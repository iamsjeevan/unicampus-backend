# tests/test_general_routes.py

import json

def test_health_check(client): # 'client' is injected by pytest from conftest.py
    """Test the /health endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data.decode('utf-8')) # Or response.get_json() if available
    assert data == {"status": "healthy"}

def test_get_app_info(client):
    """Test the /api/v1/app/info endpoint."""
    response = client.get('/api/v1/app/info')
    assert response.status_code == 200
    
    json_data = response.get_json() # Flask's test client provides this helper
    assert json_data is not None
    assert json_data['status'] == 'success'
    
    assert 'data' in json_data
    app_data = json_data['data']
    
    assert 'appName' in app_data
    assert app_data['appName'] == "UniCampus MSRIT" # Or whatever you set
    assert 'version' in app_data
    assert 'developerInfo' in app_data
    assert 'links' in app_data