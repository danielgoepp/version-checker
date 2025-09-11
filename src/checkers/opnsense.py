import json
import config
from .utils import http_get

def get_opnsense_version(instance, url=None):
    if not url:
        print(f"  {instance}: No URL configured")
        return None
        
    auth = (config.OPNSENSE_API_KEY, config.OPNSENSE_API_SECRET)
    
    info_url = f"{url}/api/core/firmware/info"
    info_data = http_get(info_url, auth=auth, timeout=15)
    if not info_data:
        print(f"  {instance}: Error getting version info")
        return None
        
    current_version = info_data.get('product_version', 'Unknown')
    full_version = info_data.get('product_version_string', current_version)
    print(f"  {instance}: Current version {current_version} (full: {full_version})")
    
    status_url = f"{url}/api/core/firmware/status"
    status_data = http_get(status_url, auth=auth, timeout=15)
    if not status_data:
        print(f"  {instance}: Could not check for updates")
        return {'current_version': current_version, 'full_version': full_version,
               'firmware_update_available': False, 'update_details': ''}
    
    if status_data.get('status') == 'update':
        upgrade_packages = status_data.get('upgrade_packages', [])
        for pkg in upgrade_packages:
            if pkg.get('name') == 'opnsense':
                full_version = pkg.get('new_version', current_version)
                break
        print(f"  {instance}: Updates available")
        return {'current_version': current_version, 'full_version': full_version,
               'firmware_update_available': True, 'update_details': json.dumps(status_data)}
    elif status_data.get('status') == 'ok':
        print(f"  {instance}: Up to date")
    else:
        print(f"  {instance}: Status unknown")
        
    return {'current_version': current_version, 'full_version': full_version,
           'firmware_update_available': False, 'update_details': json.dumps(status_data)}