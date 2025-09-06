from .base import APIChecker

def get_esphome_version(url):
    checker = APIChecker("ESPHome", url)
    
    # Try version endpoint first
    version = checker.get_json_api_version("version", version_field="version")
    if version:
        return version
    
    # Fallback to HTML parsing
    version = checker.get_text_api_version("", r'ESPHome\s+v?(\d+\.\d+\.\d+)')
    if version:
        return version
        
    print("  ESPHome: Could not get version")
    return None