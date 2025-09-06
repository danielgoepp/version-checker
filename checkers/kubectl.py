import json
from .base import KubernetesChecker
from .utils import parse_json_version


class TelegrafChecker(KubernetesChecker):
    """Checker for Telegraf instances in Kubernetes"""
    
    def __init__(self, instance):
        super().__init__(instance, namespace="telegraf")
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


def get_telegraf_version(instance):
    """Get Telegraf version from Kubernetes pod for a specific instance"""
    return TelegrafChecker(instance).get_version()


def get_calico_version(instance):
    """Get Calico version from Kubernetes daemonset"""
    checker = ImageVersionChecker(instance, namespace="calico-system")
    return checker.get_version_from_image("daemonset", "calico-node", "calico/node")


def get_metallb_version(instance):
    """Get MetalLB version from Kubernetes deployment"""
    checker = ImageVersionChecker(instance, namespace="metallb-system")
    return checker.get_version_from_image("deployment", "metallb-controller", "metallb/controller")


def get_alertmanager_version(instance):
    """Get Alertmanager version from Kubernetes statefulset"""
    checker = ImageVersionChecker(instance, namespace="alertmanager")
    return checker.get_version_from_image("statefulset", "alertmanager", "prometheus/alertmanager")


def get_fluentbit_version(instance):
    """Get Fluent Bit version from Kubernetes daemonset image"""
    checker = ImageVersionChecker(instance, namespace="fluent-bit")
    return checker.get_version_from_image("daemonset", "fluent-bit", "fluent-bit")


def get_pgadmin_version(instance):
    """Get pgAdmin version from Kubernetes deployment image"""
    checker = ImageVersionChecker(instance, namespace="pgadmin")
    return checker.get_version_from_image("deployment", "pgadmin-pgadmin4", "pgadmin4")


def get_mosquitto_version(instance):
    """Get Mosquitto MQTT broker version from Kubernetes pod"""
    checker = KubernetesChecker(instance, namespace="mosquitto")
    pod_name = checker.find_pod("mosquitto")
    
    if not pod_name:
        return None
    
    output = checker.exec_pod_command(pod_name, "mosquitto -h")
    if output:
        # Parse first line: "mosquitto version 2.0.22"
        first_line = output.split("\n")[0] if output else ""
        return checker.get_version_from_command_output(first_line, r"mosquitto version (\d+\.\d+\.\d+)")


def get_opensearch_version(instance):
    """Get OpenSearch version from Kubernetes pod API"""
    checker = PodAPIChecker(instance, namespace="opensearch")
    return checker.get_version_from_pod_api(
        "opensearch2-cluster-master-0",
        "curl -s http://localhost:9200",
        "version.number"
    )


def get_mongodb_version(instance):
    """Get MongoDB version from Kubernetes pod command"""
    checker = KubernetesChecker(instance, namespace="mongodb")
    pod_name = checker.find_pod("mongodb-0")
    
    if not pod_name:
        return None
    
    output = checker.exec_pod_command(pod_name, "mongod --version", container="mongod")
    if output:
        # Parse "db version v6.0.8" format
        return checker.get_version_from_command_output(output, r"db version v(\d+\.\d+\.\d+)")


def get_victoriametrics_version(instance):
    """Get VictoriaMetrics version from Kubernetes pod for a specific instance"""
    checker = KubernetesChecker(instance, namespace="victoriametrics")
    
    # Configure instance-specific parameters
    if instance == "operator":
        pod_pattern = "vmoperator"
        # For operator, get version from image
        image_checker = ImageVersionChecker(instance, namespace="victoriametrics")
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