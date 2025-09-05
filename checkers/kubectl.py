import subprocess
import re

def switch_kubectl_context(context):
    """Switch kubectl context and return success status"""
    try:
        cmd = f"kubectl config use-context {context}"
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def get_telegraf_version(instance):
    """Get Telegraf version from Kubernetes pod for a specific instance"""
    try:
        # Map instance names to pod prefixes
        pod_prefixes = {"vm": "telegraf-vm", "graylog": "telegraf-graylog"}

        if instance not in pod_prefixes:
            print(f"  {instance}: Unknown Telegraf instance")
            return None

        pod_prefix = pod_prefixes[instance]

        # First, get the pod name
        get_pod_cmd = f"kubectl get pods -n telegraf | grep {pod_prefix} | grep Running | head -1 | awk '{{print $1}}'"
        pod_result = subprocess.run(
            get_pod_cmd, shell=True, capture_output=True, text=True, timeout=10
        )

        if pod_result.returncode != 0 or not pod_result.stdout.strip():
            print(f"  {instance}: Could not find running {pod_prefix} pod")
            return None

        pod_name = pod_result.stdout.strip()
        print(f"  {instance}: Found pod {pod_name}")

        # Execute telegraf --version in the pod
        version_cmd = f"kubectl exec -n telegraf {pod_name} -- telegraf --version"
        version_result = subprocess.run(
            version_cmd, shell=True, capture_output=True, text=True, timeout=15
        )

        if version_result.returncode == 0:
            # Parse output like "Telegraf 1.35.4 (git: HEAD@c93eb6a0)"
            output = version_result.stdout.strip()
            version_match = re.search(r"Telegraf\s+(\d+\.\d+\.\d+)", output)
            if version_match:
                version = version_match.group(1)
                print(f"  {instance}: {version}")
                return version
            else:
                print(f"  {instance}: Could not parse version from: {output}")
                return None
        else:
            print(
                f"  {instance}: Error executing telegraf --version: {version_result.stderr}"
            )
            return None

    except subprocess.TimeoutExpired:
        print(f"  {instance}: Timeout getting version")
        return None
    except Exception as e:
        print(f"  {instance}: Error getting version - {e}")
        return None


def get_calico_version(instance):
    """Get Calico version from Kubernetes daemonset"""
    try:
        # Get Calico node daemonset image version
        describe_cmd = "kubectl describe daemonset calico-node -n calico-system | grep 'Image:' | grep calico/node"
        describe_result = subprocess.run(
            describe_cmd, shell=True, capture_output=True, text=True, timeout=10
        )

        if describe_result.returncode == 0:
            output = describe_result.stdout.strip()
            # Look for version in image tag like "calico/node:v3.28.2"
            version_match = re.search(r"calico/node:v?(\d+\.\d+\.\d+)", output)
            if version_match:
                version = version_match.group(1)
                print(f"  {instance}: {version}")
                return version
            else:
                print(f"  {instance}: Could not parse version from image: {output}")
                return None
        else:
            print(f"  {instance}: Error getting calico-node daemonset description")
            return None

    except subprocess.TimeoutExpired:
        print(f"  {instance}: Timeout getting version")
        return None
    except Exception as e:
        print(f"  {instance}: Error getting version - {e}")
        return None


def get_mosquitto_version(instance):
    """Get Mosquitto MQTT broker version from Kubernetes pod"""
    try:
        # Find the mosquitto pod
        get_pod_cmd = f"kubectl get pods -n mosquitto | grep mosquitto | grep Running | head -1 | awk '{{print $1}}'"
        pod_result = subprocess.run(
            get_pod_cmd, shell=True, capture_output=True, text=True, timeout=10
        )

        if pod_result.returncode != 0 or not pod_result.stdout.strip():
            print(f"  {instance}: Could not find running mosquitto pod")
            return None

        pod_name = pod_result.stdout.strip()
        print(f"  {instance}: Found pod {pod_name}")

        # Execute mosquitto -h to get version (shown in first line)
        version_cmd = f"kubectl exec -n mosquitto {pod_name} -- mosquitto -h"
        version_result = subprocess.run(
            version_cmd, shell=True, capture_output=True, text=True, timeout=15
        )

        if version_result.returncode == 0:
            # Parse first line: "mosquitto version 2.0.22"
            output = version_result.stdout.strip()
            first_line = output.split("\n")[0] if output else ""

            version_match = re.search(r"mosquitto version (\d+\.\d+\.\d+)", first_line)
            if version_match:
                version = version_match.group(1)
                print(f"  {instance}: {version}")
                return version
            else:
                print(f"  {instance}: Could not parse version from: {first_line}")
                return None
        else:
            print(
                f"  {instance}: Error executing mosquitto -h: {version_result.stderr}"
            )
            return None

    except subprocess.TimeoutExpired:
        print(f"  {instance}: Timeout getting version")
        return None
    except Exception as e:
        print(f"  {instance}: Error getting version - {e}")
        return None


def get_victoriametrics_version(instance):
    """Get VictoriaMetrics version from Kubernetes pod for a specific instance"""
    try:
        # Dynamically discover pods based on instance name patterns
        if instance == "operator":
            pod_pattern = "vmoperator"
            namespace = "victoriametrics"
            version_method = "image"  # Get version from container image
            version_cmd = None
            container = None
        elif "vmagent" in instance:
            pod_pattern = "vmagent"
            namespace = "victoriametrics"
            version_method = "command"
            version_cmd = "/vmagent-prod -version"
            container = "vmagent"
        elif "vmsingle" in instance:
            pod_pattern = "vmsingle"
            namespace = "victoriametrics"
            version_method = "command"
            version_cmd = "/victoria-metrics-prod -version"
            container = None
        else:
            print(f"  {instance}: Unknown VictoriaMetrics instance type")
            return None

        # First, get the pod name using dynamic pattern
        get_pod_cmd = f"kubectl get pods -n {namespace} | grep {pod_pattern} | grep Running | head -1 | awk '{{print $1}}'"
        pod_result = subprocess.run(
            get_pod_cmd, shell=True, capture_output=True, text=True, timeout=10
        )

        if pod_result.returncode != 0 or not pod_result.stdout.strip():
            print(f"  {instance}: Could not find running {pod_pattern} pod in {namespace}")
            return None

        pod_name = pod_result.stdout.strip()
        print(f"  {instance}: Found pod {pod_name}")

        # Handle different version detection methods
        if version_method == "image":
            describe_cmd = f"kubectl describe pod {pod_name} -n {namespace} | grep 'Image:' | grep operator"
            describe_result = subprocess.run(
                describe_cmd, shell=True, capture_output=True, text=True, timeout=10
            )

            if describe_result.returncode == 0:
                output = describe_result.stdout.strip()
                # Look for version in image tag like "victoriametrics/operator:v0.53.0"
                version_match = re.search(r"operator:v?(\d+\.\d+\.\d+)", output)
                if version_match:
                    version = version_match.group(1)
                    print(f"  {instance}: {version}")
                    return version
                else:
                    print(f"  {instance}: Could not parse version from image: {output}")
                    return None
            else:
                print(f"  {instance}: Error getting pod description")
                return None

        elif version_method == "command":
            # Execute version command in the pod
            container_flag = f"-c {container}" if container else ""
            kubectl_cmd = f"kubectl exec -n {namespace} {pod_name} {container_flag} -- {version_cmd}"
            version_result = subprocess.run(
                kubectl_cmd, shell=True, capture_output=True, text=True, timeout=15
            )
            
            if version_result.returncode == 0:
                # Parse output - VictoriaMetrics typically outputs version info
                output = version_result.stdout.strip()
                # Look for version patterns like "v1.125.0" or "1.125.0"
                version_match = re.search(r"v?(\d+\.\d+\.\d+)", output)
                if version_match:
                    version = version_match.group(1)
                    print(f"  {instance}: {version}")
                    return version
                else:
                    print(f"  {instance}: Could not parse version from: {output}")
                    return None
            else:
                print(f"  {instance}: Error executing {version_cmd}: {version_result.stderr}")
                return None

    except subprocess.TimeoutExpired:
        print(f"  {instance}: Timeout getting version")
        return None
    except Exception as e:
        print(f"  {instance}: Error getting version - {e}")
        return None
