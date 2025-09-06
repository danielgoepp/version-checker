import requests
from .utils import http_get, print_error, handle_timeout_error, handle_generic_error
import config


def get_unifi_protect_version(instance, url):
    """Get UniFi Protect version from bootstrap API endpoint"""
    if not url:
        print_error(instance, "No URL provided")
        return None
    
    # Use the integration endpoint that works with API key
    base_url = url.rstrip('/')
    info_url = f"{base_url}/proxy/protect/integration/v1/meta/info"
    
    try:
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Use API key authentication if configured  
        if config.UNIFI_PROTECT_API_KEY:
            headers['X-API-KEY'] = config.UNIFI_PROTECT_API_KEY
        
        response = requests.get(info_url, headers=headers, timeout=15, verify=True)
        
        if response.status_code == 401:
            print_error(instance, "Authentication required - please configure UniFi Protect API key")
            return None
        elif response.status_code == 403:
            print_error(instance, "Access forbidden - check UniFi Protect permissions")
            return None
        elif response.status_code != 200:
            print_error(instance, f"HTTP {response.status_code} - {response.reason}")
            return None
            
        data = response.json()
        
        # The integration response contains applicationVersion field
        version = data.get('applicationVersion')
        
        if version:
            return str(version)
        else:
            print_error(instance, "Version not found in integration response")
            return None
            
    except requests.exceptions.Timeout:
        return handle_timeout_error(instance, "integration API call")
    except requests.exceptions.ConnectionError as e:
        print_error(instance, f"Connection failed: {str(e)}")
        return None
    except requests.exceptions.RequestException as e:
        return handle_generic_error(instance, str(e), "integration API call")
    except Exception as e:
        return handle_generic_error(instance, str(e), "version parsing")