import config
from .base import APIChecker
from .utils import http_get, clean_version


def get_graylog_current_version(instance, url):
    """Get current Graylog version using /api/cluster endpoint"""
    # Setup authentication
    auth = None
    if hasattr(config, 'GRAYLOG_TOKENS') and instance in config.GRAYLOG_TOKENS:
        auth = (config.GRAYLOG_TOKENS[instance], 'token')
    elif hasattr(config, 'GRAYLOG_USERNAME') and hasattr(config, 'GRAYLOG_PASSWORD'):
        auth = (config.GRAYLOG_USERNAME, config.GRAYLOG_PASSWORD)
    
    # Use APIChecker with custom auth
    import requests
    try:
        api_url = f"{url}/api/cluster"
        response = requests.get(api_url, auth=auth, headers={'Accept': 'application/json'}, timeout=15, verify=True)
        response.raise_for_status()
        data = response.json()
        
        # Find version in nested structure
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict) and 'version' in value:
                    version = value['version'].split('+')[0]  # Remove build info
                    print(f"  {instance}: {version}")
                    return version
            
            if 'version' in data:
                version = data['version'].split('+')[0]
                print(f"  {instance}: {version}")
                return version
        
        print(f"  {instance}: Version field not found in cluster API response")
        return None
        
    except Exception as e:
        print(f"  {instance}: Error getting version - {e}")
        return None

def get_graylog_latest_version_from_repo(repository):
    """Get latest Graylog version from GitHub Docker repository tags"""
    headers = {}
    if hasattr(__import__('config'), 'GITHUB_API_TOKEN') and __import__('config').GITHUB_API_TOKEN:
        headers['Authorization'] = f'token {__import__("config").GITHUB_API_TOKEN}'
    
    data = http_get(f"https://api.github.com/repos/{repository}/tags?per_page=100", headers=headers)
    if data and isinstance(data, list):
        # Filter for stable releases only
        for tag in data:
            tag_name = tag["name"]
            if (not tag_name.startswith("forwarder-") and 
                not any(suffix in tag_name for suffix in ["-rc", "-beta", "-alpha"])):
                # Return first stable tag, clean up version (e.g., "6.3.3-1" -> "6.3.3")
                return tag_name.split("-")[0] if "-" in tag_name else tag_name
    return None

def get_postgresql_latest_version_from_ghcr(repository):
    """Get latest PostgreSQL version from GitHub Container Registry packages API"""
    try:
        import requests
        
        org, package_name = repository.split('/')
        # Map package names (e.g., postgres-containers -> postgresql)
        if package_name == "postgres-containers":
            package_name = "postgresql"
        
        api_url = f"https://api.github.com/orgs/{org}/packages/container/{package_name}/versions"
        headers = {'Accept': 'application/vnd.github.v3+json'}
        
        if hasattr(config, 'GITHUB_TOKEN') and config.GITHUB_TOKEN:
            headers['Authorization'] = f'token {config.GITHUB_TOKEN}'
        
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        data = response.json()
        if not (data and isinstance(data, list)):
            return None
        
        # Extract clean version tags
        version_tags = set()
        for version_info in data:
            tags = version_info.get('metadata', {}).get('container', {}).get('tags', [])
            for tag in tags:
                # Simple version pattern check (e.g., "17.2")
                if ('.' in tag and tag.replace(".", "").replace("-", "").isdigit() and 
                    not any(suffix in tag.lower() for suffix in ['bookworm', 'bullseye', 'alpine', 'minimal', 'standard'])):
                    version_tags.add(tag)
        
        if version_tags:
            # Sort versions numerically
            def version_key(v):
                return [int(p) for p in v.split('.') if p.isdigit()]
            
            try:
                return sorted(version_tags, key=version_key, reverse=True)[0]
            except (ValueError, IndexError):
                pass
        
        return None
        
    except Exception as e:
        print(f"  Error getting PostgreSQL latest version from GHCR: {e}")
        return None

# Removed redundant check_graylog_versions function - this logic is handled in version_manager.py