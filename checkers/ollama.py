from .base import APIChecker

def get_ollama_version(instance, url):
    """Get Ollama version via API endpoint"""
    checker = APIChecker(instance, url)
    
    # Ollama API version endpoint
    version = checker.get_json_api_version("api/version", version_field="version")
    if version:
        return version
    
    return None