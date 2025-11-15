import subprocess
import json
import re

def get_k3s_current_version(instance):
    """Get current k3s version using kubectl with context switching"""
    try:
        # Switch to the appropriate kubectl context
        switch_cmd = ["kubectl", "config", "use-context", instance]
        switch_result = subprocess.run(switch_cmd, capture_output=True, text=True, timeout=10, check=False)

        if switch_result.returncode != 0:
            print(f"  {instance}: Failed to switch to kubectl context")
            return None

        # Get nodes information using kubectl
        cmd = ["kubectl", "get", "nodes", "-o", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)

        if result.returncode != 0:
            print(f"  {instance}: Error getting nodes: {result.stderr}")
            return None

        try:
            nodes_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            print(f"  {instance}: Invalid JSON response from kubectl")
            return None

        # Process nodes to find K3s version
        for node_data in nodes_data.get('items', []):
            kubelet_version = node_data['status']['nodeInfo']['kubeletVersion']

            if "+k3s" in kubelet_version:
                version_match = re.search(r"v?(\d+\.\d+\.\d+\+k3s\d+)", kubelet_version)
                if version_match:
                    version = version_match.group(1)
                    print(f"  {instance}: {version}")
                    return version

        print(f"  {instance}: No K3s nodes found")
        return None
    except subprocess.TimeoutExpired:
        print(f"  {instance}: Timeout connecting to cluster")
        return None
    except Exception as e:
        print(f"  {instance}: Error getting k3s version - {e}")
        return None