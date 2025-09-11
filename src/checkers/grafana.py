import subprocess
import json

def get_grafana_version(instance, url=None):
    """Get Grafana version using kubectl exec to call internal API"""
    try:
        # Find the Grafana pod
        get_pod_cmd = f"kubectl get pods -n grafana | grep grafana | grep Running | head -1 | awk '{{print $1}}'"
        pod_result = subprocess.run(
            get_pod_cmd, shell=True, capture_output=True, text=True, timeout=10
        )

        if pod_result.returncode != 0 or not pod_result.stdout.strip():
            print(f"  {instance}: Could not find running grafana pod")
            return None

        pod_name = pod_result.stdout.strip()
        print(f"  {instance}: Found pod {pod_name}")

        # Execute curl to Grafana health API inside the pod
        version_cmd = f'kubectl exec {pod_name} -n grafana -- curl -s http://localhost:3000/api/health'
        version_result = subprocess.run(
            version_cmd, shell=True, capture_output=True, text=True, timeout=15
        )

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

    except subprocess.TimeoutExpired:
        print(f"  {instance}: Timeout getting version")
        return None
    except Exception as e:
        print(f"  {instance}: Error getting version - {e}")
        return None