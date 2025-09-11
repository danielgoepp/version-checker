import config
from .base import APIChecker

def get_home_assistant_version(instance, url):
    """Get Home Assistant version via API"""
    token = getattr(config, 'HA_TOKENS', {}).get(instance)
    if not token:
        print(f"  {instance}: No token configured")
        return None
    
    checker = APIChecker(instance, url)
    headers = {"Authorization": f"Bearer {token}"}
    return checker.get_json_api_version("api/config", version_field="version", headers=headers)