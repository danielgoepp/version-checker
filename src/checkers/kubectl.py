import json
from .base import KubernetesChecker
from .utils import parse_json_version


class TelegrafChecker(KubernetesChecker):
    """Checker for Telegraf instances in Kubernetes"""

    def __init__(self, instance, context=None, namespace=None):
        super().__init__(instance, namespace=namespace or "telegraf", context=context)
        self.pod_prefixes = {"vm": "telegraf-vm", "graylog": "telegraf-graylog"}

    def get_version(self):
        if self.instance not in self.pod_prefixes:
            print(f"  {self.instance}: Unknown Telegraf instance")
            return None

        pod_prefix = self.pod_prefixes[self.instance]
        pod_name = self.find_pod(pod_prefix)

        if not pod_name:
            return None

        output = self.exec_pod_command(pod_name, "telegraf --version")
        if output:
            # Parse "Telegraf 1.35.4 (git: HEAD@c93eb6a0)" format
            return self.get_version_from_command_output(output, r"Telegraf\s+(\d+\.\d+\.\d+)")


class ImageVersionChecker(KubernetesChecker):
    """Generic checker for getting versions from container images"""

    def get_version_from_image(self, resource_type, resource_name, image_pattern):
        description = self.describe_resource(resource_type, resource_name)
        if description:
            return self.get_image_version_from_description(description, image_pattern)
        return None


class PodAPIChecker(KubernetesChecker):
    """Generic checker for APIs accessed within pods"""

    def get_version_from_pod_api(self, pod_pattern, api_command, version_field='version'):
        pod_name = self.find_pod(pod_pattern)
        if not pod_name:
            return None

        output = self.exec_pod_command(pod_name, api_command)
        if output:
            version = parse_json_version(output, version_field)
            if version:
                print(f"  {self.instance}: {version}")
                return version
            else:
                print(f"  {self.instance}: Version field not found in API response")
                return None
        return None


def get_telegraf_version(instance, context=None, namespace=None):
    """Get Telegraf version from Kubernetes pod for a specific instance"""
    return TelegrafChecker(instance, context=context, namespace=namespace).get_version()


def get_calico_version(instance, context=None, namespace=None):
    """Get Calico version from Kubernetes daemonset"""
    checker = ImageVersionChecker(instance, namespace=namespace or "calico-system", context=context)
    return checker.get_version_from_image("daemonset", "calico-node", "calico/node")


def get_metallb_version(instance, context=None, namespace=None):
    """Get MetalLB version from Kubernetes deployment"""
    checker = ImageVersionChecker(instance, namespace=namespace or "metallb-system", context=context)
    return checker.get_version_from_image("deployment", "metallb-controller", "metallb/controller")


def get_alertmanager_version(instance, context=None, namespace=None):
    """Get Alertmanager version from Kubernetes statefulset"""
    checker = ImageVersionChecker(instance, namespace=namespace or "alertmanager", context=context)
    return checker.get_version_from_image("statefulset", "alertmanager", "prometheus/alertmanager")


def get_fluentbit_version(instance, context=None, namespace=None):
    """Get Fluent Bit version from Kubernetes daemonset image"""
    checker = ImageVersionChecker(instance, namespace=namespace or "fluent-bit", context=context)
    return checker.get_version_from_image("daemonset", "fluent-bit", "fluent-bit")


def get_pgadmin_version(instance, context=None, namespace=None):
    """Get pgAdmin version from Kubernetes deployment image"""
    checker = ImageVersionChecker(instance, namespace=namespace or "pgadmin", context=context)
    return checker.get_version_from_image("deployment", "pgadmin-pgadmin4", "pgadmin4")


def get_mosquitto_version(instance, context=None, namespace=None):
    """Get Mosquitto MQTT broker version from Kubernetes pod"""
    checker = KubernetesChecker(instance, namespace=namespace or "mosquitto", context=context)
    pod_name = checker.find_pod("mosquitto")

    if not pod_name:
        return None

    output = checker.exec_pod_command(pod_name, "mosquitto -h")
    if output:
        # Parse first line: "mosquitto version 2.0.22"
        first_line = output.split("\n")[0] if output else ""
        return checker.get_version_from_command_output(first_line, r"mosquitto version (\d+\.\d+\.\d+)")


def get_opensearch_version(instance, context=None, namespace=None):
    """Get OpenSearch version from Kubernetes pod API"""
    checker = PodAPIChecker(instance, namespace=namespace or "opensearch", context=context)
    return checker.get_version_from_pod_api(
        "opensearch-prod-master-0",
        "curl -s http://localhost:9200",
        "version.number"
    )


def get_mongodb_version(instance, context=None, namespace=None):
    """Get MongoDB version from Kubernetes pod command or operator image for a specific instance"""
    ns = namespace or "mongodb"
    checker = KubernetesChecker(instance, namespace=ns, context=context)

    # Configure instance-specific parameters
    if instance == "operator":
        pod_pattern = "mongodb-kubernetes-operator"
        # For operator, get version from image
        image_checker = ImageVersionChecker(instance, namespace=ns, context=context)
        pod_name = image_checker.find_pod(pod_pattern)
        if pod_name:
            description = image_checker.describe_resource("pod", pod_name)
            return image_checker.get_image_version_from_description(description, "mongodb-kubernetes-operator")
    else:
        # For database instances, use the existing logic
        pod_name = checker.find_pod("mongodb-0")

        if not pod_name:
            return None

        output = checker.exec_pod_command(pod_name, "mongod --version", container="mongod")
        if output:
            # Parse "db version v6.0.8" format
            return checker.get_version_from_command_output(output, r"db version v(\d+\.\d+\.\d+)")


def get_victoriametrics_version(instance, context=None, namespace=None):
    """Get VictoriaMetrics version from Kubernetes pod for a specific instance"""
    ns = namespace or "victoriametrics"
    checker = KubernetesChecker(instance, namespace=ns, context=context)

    # Configure instance-specific parameters
    if instance == "operator":
        pod_pattern = "vmoperator"
        # For operator, get version from image
        image_checker = ImageVersionChecker(instance, namespace=ns, context=context)
        pod_name = image_checker.find_pod(pod_pattern)
        if pod_name:
            description = image_checker.describe_resource("pod", pod_name)
            return image_checker.get_image_version_from_description(description, "operator")
    elif "vmagent" in instance:
        pod_pattern = "vmagent"
        pod_name = checker.find_pod(pod_pattern)
        if pod_name:
            output = checker.exec_pod_command(pod_name, "/vmagent-prod -version", container="vmagent")
            return checker.get_version_from_command_output(output)
    elif "vmsingle" in instance:
        pod_pattern = "vmsingle"
        pod_name = checker.find_pod(pod_pattern)
        if pod_name:
            output = checker.exec_pod_command(pod_name, "/victoria-metrics-prod -version")
            return checker.get_version_from_command_output(output)
    else:
        print(f"  {instance}: Unknown VictoriaMetrics instance type")
        return None


def get_unpoller_version(instance, context=None, namespace=None):
    """Get UniFi Poller version from Kubernetes pod"""
    checker = KubernetesChecker(instance, namespace=namespace or "unpoller", context=context)
    pod_name = checker.find_pod("unpoller")

    if not pod_name:
        return None

    output = checker.exec_pod_command(pod_name, "unpoller --version")
    if output:
        # Parse UniFi Poller version output (likely format: "unpoller version v2.15.4" or similar)
        return checker.get_version_from_command_output(output, r"version\s+v?(\d+\.\d+\.\d+)")


def get_certmanager_version(instance, context=None, namespace=None):
    """Get cert-manager version from Kubernetes controller pod"""
    ns = namespace or "cert-manager"
    checker = KubernetesChecker(instance, namespace=ns, context=context)
    pod_name = checker.find_pod("cert-manager-")

    if not pod_name:
        return None

    # Get version from pod description (labels contain version info)
    description = checker.describe_resource("pod", pod_name)
    if description:
        # Look for app.kubernetes.io/version label which contains the version
        import re
        version_match = re.search(r'app\.kubernetes\.io/version=v?(\d+\.\d+\.\d+)', description)
        if version_match:
            return version_match.group(1)

        # Fallback: try to get from image tag
        image_checker = ImageVersionChecker(instance, namespace=ns, context=context)
        return image_checker.get_image_version_from_description(description, "cert-manager-controller")

    return None


def get_postfix_version(instance, context=None, namespace=None):
    """Get Postfix Docker image version from Kubernetes deployment"""
    checker = ImageVersionChecker(instance, namespace=namespace or "postfix", context=context)

    # Get the deployment description
    description = checker.describe_resource("deployment", "postfix")
    if not description:
        return None

    # Use standard semantic version pattern for Docker tags
    return checker.get_image_version_from_description(description, "boky/postfix", r"(\d+\.\d+\.\d+)")



def get_uptime_kuma_version(instance, context=None, namespace=None):
    """Get Uptime Kuma version from Kubernetes deployment image"""
    checker = ImageVersionChecker(instance, namespace=namespace or "uptime-kuma", context=context)
    return checker.get_version_from_image("deployment", "uptime-kuma", "louislam/uptime-kuma")


def get_minio_kubectl_version(instance, context=None, namespace=None):
    """Get MinIO version from Kubernetes pod using kubectl"""
    ns = namespace or "minio-tenant-goepp"
    checker = KubernetesChecker(instance, namespace=ns, context=context)

    # Try to find MinIO pod
    pod_name = checker.find_pod("minio-goepp-pool-0")

    if not pod_name:
        return None

    # Get version from pod description (image tag)
    description = checker.describe_resource("pod", pod_name)
    if description:
        # Look for image version in the pod description
        # Typically: minio/minio:RELEASE.2024-01-01T00-00-00Z or minio:latest
        image_checker = ImageVersionChecker(instance, namespace=ns, context=context)
        version = image_checker.get_image_version_from_description(description, "minio",
                                                                   version_pattern=r"RELEASE\.(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z)")

        if version:
            return version

    return None
