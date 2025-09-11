import config
from .base import APIChecker
from .utils import print_error, http_get


def check_awx_current_version(instance, target_url):
    """Check current AWX version via REST API"""
    
    # Get API token for this instance
    api_token = config.AWX_API_TOKENS.get(instance)
    if not api_token:
        print_error(instance, f"No API token configured for AWX instance '{instance}'")
        return None
    
    # Create headers with Bearer token
    headers = {'Authorization': f'Bearer {api_token}'}
    
    # Build the full URL
    url = f"{target_url.rstrip('/')}/api/v2/config/"
    
    try:
        # Make the API call
        data = http_get(url, headers=headers, timeout=15)
        
        if data and isinstance(data, dict) and 'version' in data:
            version = data['version']
            return version
        else:
            print_error(instance, "Could not get version from API response")
            return None
                
    except Exception as e:
        print_error(instance, f"Error calling AWX API: {e}")
        return None