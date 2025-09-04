from .utils import http_get, print_error, handle_timeout_error, handle_generic_error
from .github import get_github_latest_tag
import requests
import config

def get_graylog_current_version(instance, url):
    """Get current Graylog version using /api/cluster endpoint"""
    try:
        # Construct the API endpoint URL
        api_url = f"{url}/api/cluster"
        
        # Try to get Graylog token from config if available
        auth = None
        if hasattr(config, 'GRAYLOG_TOKENS') and instance in config.GRAYLOG_TOKENS:
            # Use token as username with password "token"
            auth = (config.GRAYLOG_TOKENS[instance], 'token')
        elif hasattr(config, 'GRAYLOG_USERNAME') and hasattr(config, 'GRAYLOG_PASSWORD'):
            # Use basic auth if configured
            auth = (config.GRAYLOG_USERNAME, config.GRAYLOG_PASSWORD)
        
        headers = {'Accept': 'application/json'}
        
        # Make API request
        response = requests.get(api_url, auth=auth, headers=headers, timeout=15, verify=True)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract version from cluster info
        # Look for version in the cluster nodes data
        if isinstance(data, dict):
            # Check if there are nodes in the response
            for key, value in data.items():
                if isinstance(value, dict) and 'version' in value:
                    version = value['version']
                    # Clean up version string (remove build info like +01d50e5)
                    if '+' in version:
                        version = version.split('+')[0]
                    return version
            
            # If direct version field exists
            if 'version' in data:
                version = data['version']
                if '+' in version:
                    version = version.split('+')[0]
                return version
        
        print_error(instance, "Version field not found in cluster API response")
        return None
        
    except requests.exceptions.Timeout:
        return handle_timeout_error(instance, "Graylog API request")
    except requests.exceptions.RequestException as e:
        return handle_generic_error(instance, str(e), "Graylog API request")
    except Exception as e:
        return handle_generic_error(instance, str(e), "Graylog version parsing")

def get_graylog_latest_version():
    """Get latest Graylog version from GitHub Docker repository tags"""
    # Get tags from the docker repository
    data = http_get("https://api.github.com/repos/Graylog2/graylog-docker/tags?per_page=100")
    if data and isinstance(data, list):
        # Filter out forwarder, RC, beta, and alpha tags to get stable releases
        stable_tags = [
            tag["name"] for tag in data 
            if not tag["name"].startswith("forwarder-") 
            and not any(suffix in tag["name"] for suffix in ["-rc", "-beta", "-alpha"])
        ]
        
        if stable_tags:
            latest_tag = stable_tags[0]
            # Extract version number (e.g., "6.3.3-1" -> "6.3.3")
            if "-" in latest_tag:
                version = latest_tag.split("-")[0]
            else:
                version = latest_tag
            return version
    return None

def check_graylog_versions(apps_df):
    """Check versions for all Graylog instances"""
    graylog_apps = apps_df[apps_df['Name'].str.lower() == 'graylog']
    
    if graylog_apps.empty:
        return
        
    print("Graylog:")
    
    # Get latest version from GitHub
    latest_version = get_graylog_latest_version()
    
    for _, app in graylog_apps.iterrows():
        instance = app['Instance']
        url = app['Target']
        
        if not url or str(url).lower() == 'nan':
            print_error(instance, "No URL configured")
            continue
            
        # Get current version
        current_version = get_graylog_current_version(instance, url)
        
        # Update DataFrame with results
        apps_df.loc[apps_df['Name'].str.lower() == 'graylog', 'Current_Version'] = current_version
        apps_df.loc[apps_df['Name'].str.lower() == 'graylog', 'Latest_Version'] = latest_version