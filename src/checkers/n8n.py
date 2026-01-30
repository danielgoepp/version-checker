from .base import APIChecker, KubernetesChecker

def get_n8n_version_api(instance, url):
    """Get n8n version via API endpoint"""
    checker = APIChecker(instance, url)
    
    # Try common n8n API endpoints for version information
    # n8n typically exposes health/info endpoints
    version = checker.get_json_api_version("healthz", version_field="version")
    if version:
        return version
    
    # Try alternative endpoint
    version = checker.get_json_api_version("rest/version", version_field="version")
    if version:
        return version
        
    # Try health endpoint
    return checker.get_json_api_version("health", version_field="version")

def get_n8n_version_kubectl(instance, context=None, namespace=None):
    """Get n8n version from Kubernetes pod"""
    checker = KubernetesChecker(instance, namespace=namespace or "n8n", context=context)
    
    pod_name = checker.find_pod("n8n")
    if not pod_name:
        return None
    
    output = checker.exec_pod_command(pod_name, "n8n --version")
    if output:
        # Parse n8n version output 
        return checker.get_version_from_command_output(output, r"(\d+\.\d+\.\d+)")