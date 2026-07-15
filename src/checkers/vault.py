from .base import KubernetesChecker


def get_vault_version(instance, context=None, namespace=None):
    # The k8s instance tracks the vault-k8s injector image; every other
    # instance tracks the vault server image. Same namespace, one Helm release.
    image = "hashicorp/vault-k8s" if instance == "k8s" else "hashicorp/vault"
    checker = KubernetesChecker(instance, namespace=namespace or "vault", context=context)
    return checker.get_running_image_version(image)
