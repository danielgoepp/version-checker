import subprocess
import re
from .utils import http_get, print_error, print_version, parse_image_version, extract_semantic_version


class KubernetesChecker:
    """Base class for Kubernetes-based version checking"""
    
    def __init__(self, instance, namespace=None):
        self.instance = instance
        self.namespace = namespace
    
    def find_pod(self, pod_pattern, namespace=None):
        """Find a running pod matching the given pattern"""
        ns = namespace or self.namespace
        ns_flag = f"-n {ns}" if ns else ""
        
        cmd = f"kubectl get pods {ns_flag} | grep {pod_pattern} | grep Running | head -1 | awk '{{print $1}}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout.strip():
            pod_name = result.stdout.strip()
            print(f"  {self.instance}: Found pod {pod_name}")
            return pod_name
        else:
            print_error(self.instance, f"Could not find running {pod_pattern} pod")
            return None
    
    def exec_pod_command(self, pod_name, command, namespace=None, container=None):
        """Execute a command in a pod"""
        ns = namespace or self.namespace
        ns_flag = f"-n {ns}" if ns else ""
        container_flag = f"-c {container}" if container else ""
        
        cmd = f"kubectl exec {ns_flag} {pod_name} {container_flag} -- {command}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print_error(self.instance, f"Error executing {command}: {result.stderr}")
            return None
    
    def describe_resource(self, resource_type, resource_name, namespace=None):
        """Describe a Kubernetes resource"""
        ns = namespace or self.namespace
        ns_flag = f"-n {ns}" if ns else ""
        
        cmd = f"kubectl describe {resource_type} {resource_name} {ns_flag}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print_error(self.instance, f"Error describing {resource_type} {resource_name}")
            return None
    
    def get_image_version_from_description(self, description, image_pattern, version_pattern=r"v?(\d+\.\d+(?:\.\d+)?)"):
        """Extract version from image in kubectl describe output"""
        if not description:
            return None
            
        version = parse_image_version(description, image_pattern, version_pattern)
        if version:
            print_version(self.instance, version)
            return version
        else:
            print_error(self.instance, f"Could not parse version from image: {description}")
            return None
    
    def get_version_from_command_output(self, command_output, version_pattern=r'v?(\d+\.\d+\.\d+)'):
        """Extract version from command output using regex"""
        if not command_output:
            return None
            
        version = extract_semantic_version(command_output, version_pattern)
        if version:
            print_version(self.instance, version)
            return version
        else:
            print_error(self.instance, f"Could not parse version from: {command_output}")
            return None
    
    def safe_execute(self, operation_func, *args, **kwargs):
        """Safely execute an operation with timeout and error handling"""
        try:
            return operation_func(*args, **kwargs)
        except subprocess.TimeoutExpired:
            print_error(self.instance, "Timeout during operation")
            return None
        except Exception as e:
            print_error(self.instance, f"Error during operation: {e}")
            return None


class APIChecker:
    """Base class for API-based version checking"""
    
    def __init__(self, instance, base_url=None):
        self.instance = instance
        self.base_url = base_url
    
    def get_json_api_version(self, endpoint, version_field='version', headers=None, timeout=15):
        """Get version from a JSON API endpoint"""
        try:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}" if self.base_url else endpoint
            data = http_get(url, headers=headers, timeout=timeout)
            
            if data and isinstance(data, dict) and version_field in data:
                version = data[version_field]
                print_version(self.instance, version)
                return version
            else:
                print_error(self.instance, f"Could not get {version_field} from API response")
                return None
                
        except Exception as e:
            print_error(self.instance, f"Error getting version from API: {e}")
            return None
    
    def get_text_api_version(self, endpoint, version_pattern, headers=None, timeout=15):
        """Get version from a text API response using regex"""
        try:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}" if self.base_url else endpoint
            response = http_get(url, headers=headers, timeout=timeout)
            
            if response and isinstance(response, str):
                version = extract_semantic_version(response, version_pattern)
                if version:
                    print_version(self.instance, version)
                    return version
                else:
                    print_error(self.instance, "Could not parse version from response")
                    return None
            else:
                print_error(self.instance, "Could not get response from API")
                return None
                
        except Exception as e:
            print_error(self.instance, f"Error getting version from API: {e}")
            return None