from .base import APIChecker

def get_hertzbeat_version(instance, url):
    """Get HerzBeat version via API endpoints"""
    checker = APIChecker(instance, url)
    
    # Try common health/actuator endpoints for version information
    endpoints = [
        ('actuator/health', 'version'),
        ('api/actuator/health', 'version'),
        ('actuator/info', 'version'),
        ('api/actuator/info', 'version'),
        ('api/health', 'version'),
        ('health', 'version'),
        ('api/v1/health', 'version'),
        ('api/system/info', 'version'),
        ('system/info', 'version')
    ]
    
    for endpoint, version_field in endpoints:
        version = checker.get_json_api_version(endpoint, version_field)
        if version:
            return version
    
    # If no version found in JSON endpoints, try common version-specific endpoints
    version_endpoints = [
        'version',
        'api/version', 
        'api/v1/version'
    ]
    
    for endpoint in version_endpoints:
        try:
            version = checker.get_text_api_version(endpoint, r'v?(\d+\.\d+(?:\.\d+)?)')
            if version:
                return version
        except:
            continue
    
    print(f"  {instance}: Could not retrieve version from any known endpoints")
    return None