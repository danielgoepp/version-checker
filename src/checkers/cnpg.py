import subprocess
import re
import yaml
import json
from .utils import http_get

def get_cnpg_version(instance, context=None, namespace=None):
    if instance == 'operator':
        return _get_cnpg_operator_version(instance, context=context, namespace=namespace)
    else:
        return _get_postgres_cluster_version(instance, context=context, namespace=namespace)


def get_cnpg_postgres_latest_version():
    try:
        url = "https://raw.githubusercontent.com/cloudnative-pg/artifacts/main/image-catalogs/catalog-standard-trixie.yaml"
        response = http_get(url, timeout=10)
        if not response:
            print("  Error fetching CNPG catalog")
            return None

        try:
            catalog_data = yaml.safe_load(response)
        except yaml.YAMLError as e:
            print(f"  Error parsing CNPG catalog YAML: {e}")
            return None

        versions = []

        if isinstance(catalog_data, dict) and 'spec' in catalog_data:
            spec = catalog_data['spec']
            if isinstance(spec, dict) and 'images' in spec:
                for image_entry in spec['images']:
                    if isinstance(image_entry, dict) and 'image' in image_entry:
                        image_url = image_entry['image']
                        version_match = re.search(r'postgresql:(\d+\.\d+)-', str(image_url))
                        if version_match:
                            versions.append(version_match.group(1))

        if versions:
            version_tuples = [tuple(map(int, v.split('.'))) for v in versions]
            latest_tuple = max(version_tuples)
            return '.'.join(map(str, latest_tuple))

        return None

    except Exception as e:
        print(f"  Error getting CNPG latest version: {e}")
        return None


def _kubectl_cmd(context, *args):
    cmd = ["kubectl"]
    if context:
        cmd.extend(["--context", context])
    cmd.extend(args)
    return cmd


def _get_cnpg_operator_version(instance, context=None, namespace=None):
    try:
        ns = namespace or "cnpg-system"
        cmd = _kubectl_cmd(context, "get", "pods", "-n", ns, "-o", "json")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)

        if result.returncode != 0:
            print(f"  {instance}: Error getting cnpg operator pods")
            return None

        pods_data = json.loads(result.stdout)

        for pod in pods_data.get('items', []):
            containers = pod.get('spec', {}).get('containers', [])
            for container in containers:
                image = container.get('image', '')
                if 'cloudnative-pg' in image:
                    version_match = re.search(r"cloudnative-pg:v?(\d+\.\d+\.\d+)", image)
                    if version_match:
                        version = version_match.group(1)
                        print(f"  {instance}: {version}")
                        return version

        print(f"  {instance}: Could not find cloudnative-pg image")
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


def _get_postgres_cluster_version(instance, context=None, namespace=None):
    try:
        if not namespace:
            print(f"  {instance}: No namespace configured")
            return None

        pod_pattern = instance

        cmd = _kubectl_cmd(context, "get", "pods", "-n", namespace, "-o", "json")
        pod_result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)

        if pod_result.returncode != 0:
            print(f"  {instance}: Error getting pods in {namespace}")
            return None

        pods_data = json.loads(pod_result.stdout)

        pod_name = None
        for pod in pods_data.get('items', []):
            name = pod.get('metadata', {}).get('name', '')
            status = pod.get('status', {}).get('phase', '')

            if pod_pattern in name and status == 'Running':
                pod_name = name
                break

        if not pod_name:
            print(f"  {instance}: Could not find running {pod_pattern} pod in {namespace}")
            return None

        print(f"  {instance}: Found pod {pod_name}")

        version_cmd = _kubectl_cmd(context, "exec", pod_name, "-n", namespace, "--", "psql", "-t", "-c", "SELECT version();")
        version_result = subprocess.run(version_cmd, capture_output=True, text=True, timeout=15, check=False)

        if version_result.returncode == 0:
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

    except json.JSONDecodeError as e:
        print(f"  {instance}: Failed to parse kubectl output: {e}")
        return None
    except subprocess.TimeoutExpired:
        print(f"  {instance}: Timeout getting version")
        return None
    except Exception as e:
        print(f"  {instance}: Error getting version - {e}")
        return None
