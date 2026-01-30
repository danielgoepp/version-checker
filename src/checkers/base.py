import subprocess
import re
import json
from .utils import http_get, print_error, print_version, parse_image_version, extract_semantic_version


class KubernetesChecker:
    """Base class for Kubernetes-based version checking"""

    def __init__(self, instance, namespace=None, context=None):
        self.instance = instance
        self.namespace = namespace
        self.context = context

    def _kubectl_cmd(self, *args):
        """Build a kubectl command with optional --context flag"""
        cmd = ["kubectl"]
        if self.context:
            cmd.extend(["--context", self.context])
        cmd.extend(args)
        return cmd

    def find_pod(self, pod_pattern, namespace=None):
        """Find a running pod matching the given pattern using kubectl JSON output"""
        ns = namespace or self.namespace

        # Build command as list for security
        cmd = self._kubectl_cmd("get", "pods", "-o", "json")
        if ns:
            cmd.extend(["-n", ns])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)

            if result.returncode != 0:
                print_error(self.instance, f"kubectl get pods failed: {result.stderr}")
                return None

            # Parse JSON output
            pods_data = json.loads(result.stdout)

            # Filter for running pods matching pattern
            for pod in pods_data.get('items', []):
                pod_name = pod.get('metadata', {}).get('name', '')
                status = pod.get('status', {}).get('phase', '')

                if pod_pattern in pod_name and status == 'Running':
                    print(f"  {self.instance}: Found pod {pod_name}")
                    return pod_name

            print_error(self.instance, f"Could not find running {pod_pattern} pod")
            return None

        except json.JSONDecodeError as e:
            print_error(self.instance, f"Failed to parse kubectl output: {e}")
            return None
        except subprocess.TimeoutExpired:
            print_error(self.instance, "kubectl get pods timed out")
            return None

    def exec_pod_command(self, pod_name, command, namespace=None, container=None):
        """Execute a command in a pod"""
        ns = namespace or self.namespace

        # Build command as list for security
        cmd = self._kubectl_cmd("exec")
        if ns:
            cmd.extend(["-n", ns])
        cmd.append(pod_name)
        if container:
            cmd.extend(["-c", container])
        cmd.append("--")

        # Split command string into arguments if it's a string
        if isinstance(command, str):
            cmd.extend(command.split())
        else:
            cmd.extend(command)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print_error(self.instance, f"Error executing {command}: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print_error(self.instance, f"kubectl exec timed out for command: {command}")
            return None

    def describe_resource(self, resource_type, resource_name, namespace=None):
        """Describe a Kubernetes resource"""
        ns = namespace or self.namespace

        # Build command as list for security
        cmd = self._kubectl_cmd("describe", resource_type, resource_name)
        if ns:
            cmd.extend(["-n", ns])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print_error(self.instance, f"Error describing {resource_type} {resource_name}")
                return None

        except subprocess.TimeoutExpired:
            print_error(self.instance, f"kubectl describe timed out for {resource_type} {resource_name}")
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