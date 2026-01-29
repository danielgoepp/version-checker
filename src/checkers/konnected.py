from .utils import http_get, print_error, print_version

def get_konnected_current_version(instance, url=None):
    """Get current version from Konnected ESPHome device via native API"""
    if not url:
        print_error(instance, "No device URL configured")
        return None
    
    try:
        import asyncio
        import aioesphomeapi
        from urllib.parse import urlparse
        
        # Parse the URL to get hostname
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        
        if not hostname:
            print_error(instance, "Could not parse hostname from URL")
            return None
        
        async def get_esphome_device_info():
            try:
                # Connect to ESPHome device
                api = aioesphomeapi.APIClient(hostname, 6053, "")
                await api.connect(login=False)  # Try without password first
                
                # Get device info which includes version
                device_info = await api.device_info()
                
                # Also try to get entity states which might include firmware version
                entities = await api.list_entities_services()
                
                await api.disconnect()
                
                # Look for Konnected firmware version in project_version field
                if hasattr(device_info, 'project_version') and device_info.project_version:
                    return device_info.project_version
                
                # Fallback to firmware_version if available
                if hasattr(device_info, 'firmware_version') and device_info.firmware_version:
                    return device_info.firmware_version
                
                # Last fallback to ESPHome version
                if hasattr(device_info, 'esphome_version') and device_info.esphome_version:
                    return device_info.esphome_version
                
                return None
                
            except Exception as e:
                return f"Error: {str(e)}"
        
        # Run the async function
        try:
            version = asyncio.run(get_esphome_device_info())
            
            if version and not version.startswith("Error:"):
                print_version(instance, f"ESPHome version: {version}")
                return version
            elif version:
                print_error(instance, version)
                return None
            else:
                print_error(instance, "No version info found in device response")
                return None
                
        except Exception as e:
            print_error(instance, f"ESPHome API error: {str(e)}")
            return None
            
    except ImportError:
        print_error(instance, "aioesphomeapi module not available")
        return None

def get_konnected_version(instance, url=None, github_repo=None):
    if not github_repo:
        print_error(instance, "No GitHub repository configured")
        return None
    
    github_url = f"https://raw.githubusercontent.com/{github_repo}/master/garage-door-GDOv2-Q.yaml"
    yaml_content = http_get(github_url)
    if yaml_content and isinstance(yaml_content, str):
        for line in yaml_content.split('\n'):
            if line.strip().startswith('project_version:'):
                version = line.split(':', 1)[1].strip().strip('"\'')
                print_version(instance, version)
                return version
    
    print_error(instance, "Could not get project version")
    return None