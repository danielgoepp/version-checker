import re
from .utils import http_get

def get_esphome_version(url):
    # Try version endpoint first
    data = http_get(f"{url}/version")
    if data:
        version = data.get('version', str(data).strip()) if isinstance(data, dict) else str(data).strip()
        print(f"  ESPHome: {version}")
        return version
        
    # Fallback to HTML parsing
    html = http_get(url)
    if html and isinstance(html, str):
        match = re.search(r'ESPHome\s+v?(\d+\.\d+\.\d+)', html)
        if match:
            version = match.group(1)
            print(f"  ESPHome: {version}")
            return version
            
    print(f"  ESPHome: Could not get version")
    return None