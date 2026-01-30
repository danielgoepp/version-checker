import subprocess
import json

def get_grafana_version(instance, url=None, context=None, namespace=None):
    """Get Grafana version using kubectl exec to call internal API"""
    try:
        ns = namespace or "grafana"
        # Build kubectl base command with optional context
        def _kubectl_cmd(*args):
            cmd = ["kubectl"]
            if context:
                cmd.extend(["--context", context])
            cmd.extend(args)
            return cmd

        # Find the Grafana pod using JSON output
        cmd = _kubectl_cmd("get", "pods", "-n", ns, "-o", "json")
        pod_result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)

        if pod_result.returncode != 0:
            print(f"  {instance}: Error getting grafana pods")
            return None

        # Parse JSON output
        pods_data = json.loads(pod_result.stdout)

        # Find running Grafana pod
        pod_name = None
        for pod in pods_data.get('items', []):
            name = pod.get('metadata', {}).get('name', '')
            status = pod.get('status', {}).get('phase', '')

            if 'grafana' in name and status == 'Running':
                pod_name = name
                break

        if not pod_name:
            print(f"  {instance}: Could not find running grafana pod")
            return None

        print(f"  {instance}: Found pod {pod_name}")

        # Execute curl to Grafana health API inside the pod
        version_cmd = _kubectl_cmd("exec", pod_name, "-n", ns, "--", "curl", "-s", "http://localhost:3000/api/health")
        version_result = subprocess.run(version_cmd, capture_output=True, text=True, timeout=15, check=False)

        if version_result.returncode == 0:
            # Parse JSON output to extract version
            try:
                output = version_result.stdout.strip()
                data = json.loads(output)
                if 'version' in data:
                    version = data['version']
                    print(f"  {instance}: {version}")
                    return version
                else:
                    print(f"  {instance}: Version field not found in health API response")
                    return None
            except json.JSONDecodeError:
                print(f"  {instance}: Could not parse JSON response: {output}")
                return None
        else:
            print(f"  {instance}: Error executing Grafana health API call: {version_result.stderr}")
            return None

    except json.JSONDecodeError as e:
        print(f"  {instance}: Failed to parse kubectl output: {e}")
        return None
    except subprocess.TimeoutExpired:
        print(f"  {instance}: Timeout getting version")
        return None
    except Exception as e:
        print(f"  {instance}: Error getting version - {e}")
        return None