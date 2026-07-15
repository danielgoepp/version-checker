from .base import KubernetesChecker

def get_n8n_version_kubectl(instance, context=None, namespace=None):
    checker = KubernetesChecker(instance, namespace=namespace or "n8n", context=context)

    pod_name = checker.find_pod("n8n")
    if not pod_name:
        return None

    output = checker.exec_pod_command(pod_name, "n8n --version")
    if output:
        return checker.get_version_from_command_output(output, r"(\d+\.\d+\.\d+)")
