import requests
from .utils import http_get, print_error


def get_open_webui_version(instance, url):
    """
    Get current Open WebUI version from /api/version endpoint
    
    Args:
        instance: Instance name (e.g., 'adambalm')
        url: Base URL of Open WebUI instance
    
    Returns:
        Version string or None if failed
    """
    try:
        # Open WebUI /api/version endpoint
        version_url = f"{url}/api/version"
        
        response = requests.get(version_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        version = data.get('version')
        
        if version:
            return version
        else:
            print_error(instance, "No version field found in response")
            return None
            
    except requests.exceptions.RequestException as e:
        print_error(instance, f"Failed to connect to Open WebUI API: {e}")
        return None
    except Exception as e:
        print_error(instance, f"Error getting Open WebUI version: {e}")
        return None