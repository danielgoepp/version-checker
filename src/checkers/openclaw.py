from .base import KubernetesChecker


def get_openclaw_version(instance, context=None, namespace=None):
    checker = KubernetesChecker(instance, namespace=namespace or "openclaw", context=context)

    pod_name = checker.find_pod("openclaw")
    if not pod_name:
        return None

    output = checker.exec_pod_command(pod_name, ["node", "-e", "process.stdout.write(require('/app/package.json').version)"])
    if output:
        return checker.get_version_from_command_output(output, r"(\d{4}\.\d+\.\d+|\d+\.\d+\.\d+)")
