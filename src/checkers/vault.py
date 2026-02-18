from .base import APIChecker


def get_vault_version(instance, url):
    """Get HashiCorp Vault version from sys/health API endpoint"""
    checker = APIChecker(instance, url)
    return checker.get_json_api_version("v1/sys/health", version_field="version")
