import subprocess
import re

def get_cnpg_operator_version(instance):
    """Get CloudNativePG operator version from Kubernetes deployment"""
    try:
        # Get CNPG operator deployment image version
        describe_cmd = "kubectl describe pod -n cnpg-system | grep 'Image:' | grep cloudnative-pg"
        describe_result = subprocess.run(
            describe_cmd, shell=True, capture_output=True, text=True, timeout=10
        )

        if describe_result.returncode == 0:
            output = describe_result.stdout.strip()
            # Look for version in image tag like "ghcr.io/cloudnative-pg/cloudnative-pg:1.25.0"
            version_match = re.search(r"cloudnative-pg:v?(\d+\.\d+\.\d+)", output)
            if version_match:
                version = version_match.group(1)
                print(f"  {instance}: {version}")
                return version
            else:
                print(f"  {instance}: Could not parse version from image: {output}")
                return None
        else:
            print(f"  {instance}: Error getting cnpg operator description")
            return None

    except subprocess.TimeoutExpired:
        print(f"  {instance}: Timeout getting version")
        return None
    except Exception as e:
        print(f"  {instance}: Error getting version - {e}")
        return None


def get_postgres_version(instance):
    """Get PostgreSQL version from CNPG cluster instances"""
    try:
        # Map instance names to namespaces and pod patterns based on full instance names
        instance_mapping = {
            "grafana-prod": {"namespace": "cnpg-grafana", "pod_pattern": "grafana-prod"},
            "hertzbeat-prod": {"namespace": "cnpg-hertzbeat", "pod_pattern": "hertzbeat-prod"},
            "homeassistant-prod": {"namespace": "cnpg-homeassistant", "pod_pattern": "homeassistant-prod"}
        }

        if instance not in instance_mapping:
            print(f"  {instance}: Unknown PostgreSQL instance")
            return None

        mapping = instance_mapping[instance]
        namespace = mapping["namespace"]
        pod_pattern = mapping["pod_pattern"]

        # First, get a running pod name for this instance
        get_pod_cmd = f"kubectl get pods -n {namespace} | grep {pod_pattern} | grep Running | head -1 | awk '{{print $1}}'"
        pod_result = subprocess.run(
            get_pod_cmd, shell=True, capture_output=True, text=True, timeout=10
        )

        if pod_result.returncode != 0 or not pod_result.stdout.strip():
            print(f"  {instance}: Could not find running {pod_pattern} pod in {namespace}")
            return None

        pod_name = pod_result.stdout.strip()
        print(f"  {instance}: Found pod {pod_name}")

        # Execute psql to get PostgreSQL version
        version_cmd = f'kubectl exec {pod_name} -n {namespace} -- psql -t -c "SELECT version();"'
        version_result = subprocess.run(
            version_cmd, shell=True, capture_output=True, text=True, timeout=15
        )

        if version_result.returncode == 0:
            # Parse output like "PostgreSQL 17.2 (Debian 17.2-1.pgdg110+1) on x86_64-pc-linux-gnu..."
            output = version_result.stdout.strip()
            version_match = re.search(r"PostgreSQL\s+(\d+\.\d+)", output)
            if version_match:
                version = version_match.group(1)
                print(f"  {instance}: {version}")
                return version
            else:
                print(f"  {instance}: Could not parse version from: {output}")
                return None
        else:
            print(f"  {instance}: Error executing psql version command: {version_result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        print(f"  {instance}: Timeout getting version")
        return None
    except Exception as e:
        print(f"  {instance}: Error getting version - {e}")
        return None