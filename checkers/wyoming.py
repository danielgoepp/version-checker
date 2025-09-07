from .base import KubernetesChecker
import subprocess
from .utils import print_error

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


def get_wyoming_satellite_version(instance, host):
    """
    Get Wyoming Satellite version via SSH command
    
    Args:
        instance: Instance name (e.g., 'voicepi-greatroom')
        host: Host address for SSH connection
    
    Returns:
        Version string or None if failed
    """
    try:
        # Try multiple methods to get Wyoming Satellite version
        
        # Method 1: Check if it's installed as a pip package
        result = subprocess.run([
            'ssh', host, 
            'pip3 show wyoming-satellite 2>/dev/null | grep Version: || pip show wyoming-satellite 2>/dev/null | grep Version:'
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0 and result.stdout.strip():
            # Parse "Version: 1.4.1" format
            for line in result.stdout.strip().split('\n'):
                if line.startswith('Version:'):
                    version = line.split(':', 1)[1].strip()
                    if version:
                        return version
        
        # Method 2: Check git tag if installed from source in /opt or home
        result = subprocess.run([
            'ssh', host,
            'cd /opt/wyoming-satellite 2>/dev/null && git describe --tags 2>/dev/null || cd ~/wyoming-satellite 2>/dev/null && git describe --tags 2>/dev/null || echo "No git repo"'
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0 and result.stdout.strip() and 'No git repo' not in result.stdout:
            version = result.stdout.strip()
            # Remove 'v' prefix if present
            if version.startswith('v'):
                version = version[1:]
            return version
        
        # Method 3: Check pip in virtual environment
        result = subprocess.run([
            'ssh', host,
            '/opt/wyoming-satellite/venv/bin/pip show wyoming-satellite 2>/dev/null | grep Version: || echo "Not found"'
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0 and result.stdout.strip() and 'Not found' not in result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.startswith('Version:'):
                    version = line.split(':', 1)[1].strip()
                    if version:
                        return version
        
        # Method 4: Try to find version in Python module
        result = subprocess.run([
            'ssh', host,
            '/opt/wyoming-satellite/venv/bin/python -c "import wyoming_satellite; print(wyoming_satellite.__version__)" 2>/dev/null || python3 -c "import wyoming_satellite; print(wyoming_satellite.__version__)" 2>/dev/null || echo "Not found"'
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0 and result.stdout.strip() and 'Not found' not in result.stdout:
            return result.stdout.strip()
            
        print_error(instance, "Unable to determine Wyoming Satellite version")
        return None
        
    except subprocess.TimeoutExpired:
        print_error(instance, "SSH command timed out")
        return None
    except subprocess.SubprocessError as e:
        print_error(instance, f"SSH command failed: {e}")
        return None
    except Exception as e:
        print_error(instance, f"Error getting Wyoming Satellite version: {e}")
        return None