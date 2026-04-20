from .base import APIChecker

def get_ollama_version(instance, url):
    checker = APIChecker(instance, url)

    version = checker.get_json_api_version("api/version", version_field="version")
    if version:
        return version

    return None