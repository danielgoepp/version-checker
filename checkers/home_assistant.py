import config
from .utils import http_get, print_error, print_version

def get_home_assistant_version(instance, url):
    """Get Home Assistant version via API"""
    token = getattr(config, 'HA_TOKENS', {}).get(instance)
    if not token:
        print_error(instance, "No token configured")
        return None
        
    data = http_get(f"{url}/api/config", headers={"Authorization": f"Bearer {token}"})
    if data and 'version' in data:
        version = data['version']
        print_version(instance, version)
        return version
    
    print_error(instance, "Error getting version")
    return None