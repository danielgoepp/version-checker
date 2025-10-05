import subprocess
import re
import yaml
from .utils import http_get

def get_cnpg_version(instance):
    """
    Unified CNPG version checker for both operator and PostgreSQL cluster instances.

    - operator: Checks CNPG operator deployment version
    - PostgreSQL instances: Checks PostgreSQL version in CNPG cluster pods
    """
    if instance == 'operator':
        return _get_cnpg_operator_version(instance)
    else:
        return _get_postgres_cluster_version(instance)


def get_cnpg_postgres_latest_version():
    """Get latest PostgreSQL version from CNPG artifacts catalog for Debian Trixie"""
    try:
        # Fetch the catalog YAML from cloudnative-pg/artifacts repository
        url = "https://raw.githubusercontent.com/cloudnative-pg/artifacts/main/image-catalogs/catalog-standard-trixie.yaml"

        response = http_get(url, timeout=10)
        if not response:
            print("  Error fetching CNPG catalog")
            return None

        # Parse YAML
        try:
            catalog_data = yaml.safe_load(response)
        except yaml.YAMLError as e:
            print(f"  Error parsing CNPG catalog YAML: {e}")
            return None

        # Extract latest PostgreSQL version
        # The catalog structure has images in spec.images with image URLs
        # Example: ghcr.io/cloudnative-pg/postgresql:18.0-202509290807-standard-trixie@sha256:...
        versions = []

        if isinstance(catalog_data, dict) and 'spec' in catalog_data:
            spec = catalog_data['spec']
            if isinstance(spec, dict) and 'images' in spec:
                for image_entry in spec['images']:
                    if isinstance(image_entry, dict) and 'image' in image_entry:
                        image_url = image_entry['image']
                        # Extract version from image URL like "postgresql:18.0-..."
                        version_match = re.search(r'postgresql:(\d+\.\d+)-', str(image_url))
                        if version_match:
                            versions.append(version_match.group(1))

        if versions:
            # Sort versions and return the latest
            # Convert to tuples for proper numeric sorting
            version_tuples = [tuple(map(int, v.split('.'))) for v in versions]
            latest_tuple = max(version_tuples)
            latest_version = '.'.join(map(str, latest_tuple))
            return latest_version

        return None

    except Exception as e:
        print(f"  Error getting CNPG latest version: {e}")
        return None


def _get_cnpg_operator_version(instance):
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


def _get_postgres_cluster_version(instance):
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
