from .base import APIChecker

def get_traefik_version(instance, url):
    """Get Traefik version from API endpoint"""
    checker = APIChecker(instance, url)
    return checker.get_json_api_version("api/version", version_field="Version", timeout=15)