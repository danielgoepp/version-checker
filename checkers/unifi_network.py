import requests
from .utils import print_error, handle_timeout_error, handle_generic_error
import config


def get_unifi_network_version(instance, url):
    """Get UniFi Network version from cloud API"""
    if not config.UNIFI_NETWORK_API_KEY:
        print_error(instance, "No UniFi Network API key configured")
        return None
    
    headers = {
        "X-API-KEY": config.UNIFI_NETWORK_API_KEY,
        "Accept": "application/json",
    }
    
    try:
        # Get hosts from UniFi cloud API
        hosts_response = requests.get("https://api.ui.com/v1/hosts", headers=headers, timeout=15)
        hosts_response.raise_for_status()
        
        api_response = hosts_response.json()
        
        # Extract hosts data from the API response
        if isinstance(api_response, dict) and 'data' in api_response:
            hosts_data = api_response['data']
        else:
            hosts_data = api_response
        
        if not isinstance(hosts_data, list):
            print_error(instance, "Unexpected hosts API response format")
            return None
        
        # Look for our specific UniFi Network host
        target_hostname = None
        if url:
            # Extract hostname from URL for matching
            from urllib.parse import urlparse
            parsed = urlparse(url)
            target_hostname = parsed.hostname
        
        network_host = None
        for host in hosts_data:
            # Look for Network application type (based on the API response structure)
            if host.get('type') == 'network-server':
                # If we have a target hostname, match it
                # Note: The API doesn't seem to return hostname directly, so for now take any network host
                network_host = host
                break
        
        if not network_host:
            print_error(instance, "No UniFi Network host found in cloud API")
            return None
        
        # Extract version information from reportedState
        reported_state = network_host.get('reportedState', {})
        version = (reported_state.get('version') or 
                  reported_state.get('firmware_version') or
                  network_host.get('version'))
        
        if version:
            return str(version)
        else:
            print_error(instance, "Version not found in host information")
            return None
            
    except requests.exceptions.RequestException as e:
        print_error(instance, f"UniFi cloud API error: {str(e)}")
        return None
    except Exception as e:
        return handle_generic_error(instance, str(e), "cloud API call")