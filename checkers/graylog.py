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

def get_graylog_latest_version_from_repo(repository):
    """Get latest Graylog version from specified GitHub Docker repository tags"""
    # Get tags from the docker repository
    data = http_get(f"https://api.github.com/repos/{repository}/tags?per_page=100")
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

def get_postgresql_latest_version_from_ghcr(repository):
    """Get latest PostgreSQL version from GitHub Container Registry packages API"""
    try:
        import requests
        
        # Use GitHub Packages API to get container versions
        # Format: https://api.github.com/orgs/{org}/packages/container/{package}/versions
        org, package_name = repository.split('/')
        
        # For cloudnative-pg/postgres-containers, the package name is "postgresql"
        if package_name == "postgres-containers":
            package_name = "postgresql"
        
        api_url = f"https://api.github.com/orgs/{org}/packages/container/{package_name}/versions"
        
        # Try with GitHub token if available
        headers = {'Accept': 'application/vnd.github.v3+json'}
        if hasattr(config, 'GITHUB_TOKEN') and config.GITHUB_TOKEN:
            headers['Authorization'] = f'token {config.GITHUB_TOKEN}'
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 401:
            print("  GitHub Container Registry API requires authentication for latest PostgreSQL versions")
            return None
        elif response.status_code != 200:
            print(f"  Error accessing container registry: {response.status_code}")
            return None
        
        data = response.json()
        
        if data and isinstance(data, list):
            # Extract version tags from container registry
            version_tags = []
            for version_info in data:
                if 'metadata' in version_info and 'container' in version_info['metadata']:
                    tags = version_info['metadata']['container'].get('tags', [])
                    for tag in tags:
                        # Look for simple version patterns like "17.2", "16.4"
                        if tag.replace(".", "").replace("-", "").isdigit() and "." in tag:
                            # Filter out tags with suffixes like "17.2-bookworm"
                            if not any(suffix in tag.lower() for suffix in ['bookworm', 'bullseye', 'alpine', 'minimal', 'standard']):
                                version_tags.append(tag)
            
            if version_tags:
                # Remove duplicates and sort versions numerically
                unique_versions = list(set(version_tags))
                def version_key(v):
                    # Handle versions like "17.2" and "16.4.1"
                    parts = v.split('.')
                    return [int(p) for p in parts if p.isdigit()]
                
                try:
                    sorted_versions = sorted(unique_versions, key=version_key, reverse=True)
                    return sorted_versions[0]
                except (ValueError, IndexError):
                    pass
        
        return None
        
    except Exception as e:
        print(f"  Error getting PostgreSQL latest version from GHCR: {e}")
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