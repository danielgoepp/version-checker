from .base import KubernetesChecker

def get_wyoming_openwakeword_version(instance, namespace):
    """Get Wyoming OpenWakeWord version from running Kubernetes pod"""
    checker = KubernetesChecker(instance, namespace)
    
    # Find the pod
    pod_name = checker.find_pod("wyoming-openwakeword")
    if not pod_name:
        return None
    
    # Get version from VERSION file inside the container
    output = checker.exec_pod_command(
        pod_name, 
        "cat /usr/src/.venv/lib/python3.11/site-packages/wyoming_openwakeword/VERSION"
    )
    if output:
        version = output.strip()
        print(f"  {instance}: {version}")
        return version
    
    return None

def get_wyoming_piper_version(instance, namespace):
    """Get Wyoming Piper version from running Kubernetes pod"""
    checker = KubernetesChecker(instance, namespace)
    
    # Find the pod
    pod_name = checker.find_pod("wyoming-piper")
    if not pod_name:
        return None
    
    # Get version from pip freeze output
    output = checker.exec_pod_command(
        pod_name, 
        "pip3 freeze | grep wyoming-piper"
    )
    if output:
        # Parse "wyoming-piper @ https://github.com/rhasspy/wyoming-piper/archive/refs/tags/v1.6.3.tar.gz"
        version = checker.get_version_from_command_output(output, r"v(\d+\.\d+\.\d+)")
        if version:
            return version
    
    return None

def get_wyoming_whisper_version(instance, namespace):
    """Get Wyoming Whisper version from running Kubernetes pod"""
    checker = KubernetesChecker(instance, namespace)
    
    # Find the pod  
    pod_name = checker.find_pod("wyoming-whisper")
    if not pod_name:
        return None
    
    # Get version from pip freeze output (it's actually faster-whisper)
    output = checker.exec_pod_command(
        pod_name, 
        "pip3 freeze | grep wyoming-faster-whisper"
    )
    if output:
        # Parse "wyoming-faster-whisper @ https://github.com/rhasspy/wyoming-faster-whisper/archive/refs/tags/v2.2.0.tar.gz"
        version = checker.get_version_from_command_output(output, r"v(\d+\.\d+\.\d+)")
        if version:
            return version
    
    return None