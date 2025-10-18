import requests
import urllib3
import warnings
from .utils import http_get, print_error


def get_portainer_version(instance, url):
    """
    Get current Portainer version from /api/status endpoint
    
    Args:
        instance: Instance name (e.g., 'adambalm')
        url: Base URL of Portainer instance
    
    Returns:
        Version string or None if failed
    """
    try:
        # Portainer /api/status endpoint doesn't require authentication
        status_url = f"{url}/api/status"

        # Suppress SSL warning for this specific server
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(status_url, timeout=10, verify=False)
        response.raise_for_status()
        
        data = response.json()
        version = data.get('Version')
        
        if version:
            return version
        else:
            print_error(instance, "No version field found in status response")
            return None
            
    except requests.exceptions.RequestException as e:
        print_error(instance, f"Failed to connect to Portainer API: {e}")
        return None
    except Exception as e:
        print_error(instance, f"Error getting Portainer version: {e}")
        return None