from .base import KubernetesChecker


def get_openclaw_version(instance, context=None, namespace=None):
    # Read the running image tag rather than exec'ing in to read package.json:
    # upstream tags patch/rebuild releases with a -N suffix (e.g. 2026.7.1-2)
    # without bumping package.json's version, so package.json can't
    # distinguish which -N release is actually deployed.
    checker = KubernetesChecker(instance, namespace=namespace or "openclaw", context=context)
    return checker.get_running_image_version(
        "ghcr.io/openclaw/openclaw",
        version_pattern=r"(\d{4}\.\d+\.\d+-\d+|\d{4}\.\d+\.\d+|\d+\.\d+\.\d+-\d+|\d+\.\d+\.\d+)",
    )
