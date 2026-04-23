import json
from .base import KubernetesChecker
from .utils import parse_json_version


class TelegrafChecker(KubernetesChecker):
    def __init__(self, instance, context=None, namespace=None):
        super().__init__(instance, namespace=namespace or "telegraf", context=context)
        self.pod_prefixes = {
            "mqtt-to-vms": "telegraf-mqtt-to-vms",
            "mqtt-to-graylog": "telegraf-mqtt-to-graylog",
            "upsd-to-vms": "telegraf-upsd-to-vms",
        }

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
            return self.get_version_from_command_output(output, r"Telegraf\s+(\d+\.\d+\.\d+)")


class ImageVersionChecker(KubernetesChecker):
    def get_version_from_image(self, resource_type, resource_name, image_pattern):
        description = self.describe_resource(resource_type, resource_name)
        if description:
            return self.get_image_version_from_description(description, image_pattern)
        return None


class PodAPIChecker(KubernetesChecker):
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
    return TelegrafChecker(instance, context=context, namespace=namespace).get_version()


def get_calico_version(instance, context=None, namespace=None):
    checker = ImageVersionChecker(instance, namespace=namespace or "calico-system", context=context)
    return checker.get_version_from_image("daemonset", "calico-node", "calico/node")


def get_metallb_version(instance, context=None, namespace=None):
    checker = ImageVersionChecker(instance, namespace=namespace or "metallb-system", context=context)
    return checker.get_version_from_image("deployment", "metallb-controller", "metallb/controller")


def get_alertmanager_version(instance, context=None, namespace=None):
    checker = ImageVersionChecker(instance, namespace=namespace or "alertmanager", context=context)
    return checker.get_version_from_image("statefulset", "alertmanager", "prometheus/alertmanager")


def get_fluentbit_version(instance, context=None, namespace=None):
    checker = ImageVersionChecker(instance, namespace=namespace or "fluent-bit", context=context)
    return checker.get_version_from_image("daemonset", "fluent-bit", "fluent-bit")


def get_pgadmin_version(instance, context=None, namespace=None):
    checker = ImageVersionChecker(instance, namespace=namespace or "pgadmin", context=context)
    return checker.get_version_from_image("deployment", "pgadmin-pgadmin4", "pgadmin4")


def get_mosquitto_version(instance, context=None, namespace=None):
    checker = KubernetesChecker(instance, namespace=namespace or "mosquitto", context=context)
    pod_name = checker.find_pod("mosquitto")

    if not pod_name:
        return None

    output = checker.exec_pod_command(pod_name, "mosquitto -h")
    if output:
        first_line = output.split("\n")[0] if output else ""
        return checker.get_version_from_command_output(first_line, r"mosquitto version (\d+\.\d+\.\d+)")


def get_opensearch_version(instance, context=None, namespace=None):
    checker = PodAPIChecker(instance, namespace=namespace or "opensearch", context=context)
    return checker.get_version_from_pod_api(
        "opensearch-prod-master-0",
        "curl -s http://localhost:9200",
        "version.number"
    )


def get_mongodb_version(instance, context=None, namespace=None):
    ns = namespace or "mongodb"
    checker = KubernetesChecker(instance, namespace=ns, context=context)

    if instance == "operator":
        image_checker = ImageVersionChecker(instance, namespace=ns, context=context)
        pod_name = image_checker.find_pod("mongodb-kubernetes-operator")
        if pod_name:
            description = image_checker.describe_resource("pod", pod_name)
            return image_checker.get_image_version_from_description(description, "mongodb-kubernetes-operator")
    else:
        pod_name = checker.find_pod("mongodb-0")

        if not pod_name:
            return None

        output = checker.exec_pod_command(pod_name, "mongod --version", container="mongod")
        if output:
            return checker.get_version_from_command_output(output, r"db version v(\d+\.\d+\.\d+)")


def get_victoriametrics_version(instance, context=None, namespace=None):
    ns = namespace or "victoriametrics"
    checker = KubernetesChecker(instance, namespace=ns, context=context)

    if instance == "operator":
        image_checker = ImageVersionChecker(instance, namespace=ns, context=context)
        pod_name = image_checker.find_pod("vmoperator")
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
    checker = KubernetesChecker(instance, namespace=namespace or "unpoller", context=context)
    pod_name = checker.find_pod("unpoller")

    if not pod_name:
        return None

    output = checker.exec_pod_command(pod_name, "unpoller --version")
    if output:
        return checker.get_version_from_command_output(output, r"version\s+v?(\d+\.\d+\.\d+)")


def get_certmanager_version(instance, context=None, namespace=None):
    ns = namespace or "cert-manager"
    checker = KubernetesChecker(instance, namespace=ns, context=context)
    pod_name = checker.find_pod("cert-manager-")

    if not pod_name:
        return None

    description = checker.describe_resource("pod", pod_name)
    if description:
        import re
        version_match = re.search(r'app\.kubernetes\.io/version=v?(\d+\.\d+\.\d+)', description)
        if version_match:
            return version_match.group(1)

        image_checker = ImageVersionChecker(instance, namespace=ns, context=context)
        return image_checker.get_image_version_from_description(description, "cert-manager-controller")

    return None


def get_postfix_version(instance, context=None, namespace=None):
    checker = ImageVersionChecker(instance, namespace=namespace or "postfix", context=context)
    description = checker.describe_resource("deployment", "postfix")
    if not description:
        return None
    return checker.get_image_version_from_description(description, "boky/postfix", r"(\d+\.\d+\.\d+)")



def get_uptime_kuma_version(instance, context=None, namespace=None):
    checker = ImageVersionChecker(instance, namespace=namespace or "uptime-kuma", context=context)
    return checker.get_version_from_image("deployment", "uptime-kuma", "louislam/uptime-kuma")


def get_minio_operator_version(instance, context=None, namespace=None):
    checker = ImageVersionChecker(instance, namespace=namespace or "minio-operator", context=context)
    return checker.get_version_from_image("deployment", "minio-operator", "minio/operator")


def get_minio_kubectl_version(instance, context=None, namespace=None):
    ns = namespace or "minio-tenant-goepp"
    checker = KubernetesChecker(instance, namespace=ns, context=context)
    pod_name = checker.find_pod("minio-goepp-pool-0")

    if not pod_name:
        return None

    description = checker.describe_resource("pod", pod_name)
    if description:
        image_checker = ImageVersionChecker(instance, namespace=ns, context=context)
        return image_checker.get_image_version_from_description(description, "minio",
                                                                version_pattern=r"RELEASE\.(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z)")

    return None
