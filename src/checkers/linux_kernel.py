#!/usr/bin/env python

import subprocess
import re

_STATUS_NO_UPDATE = 'no update'
_STATUS_UPDATE_AVAILABLE = 'update available'


def get_latest_linux_kernel_version(current_kernel, target_host):
    """
    Check for available kernel updates using SSH and apt.
    Returns the new kernel version string if one is available,
    'no update' if up to date, or 'update available' as a fallback
    when the version can't be extracted.
    """
    if not target_host:
        return _STATUS_NO_UPDATE
    try:
        return check_for_kernel_updates(target_host)
    except Exception as e:
        print(f"  Error checking kernel versions: {e}")
        return _STATUS_NO_UPDATE


def check_for_kernel_updates(target_host):
    """
    Check for kernel updates via SSH using apt list --upgradable.
    Returns the new kernel version string, 'update available', or 'no update'.
    """
    try:
        print(f"    Checking for kernel updates on {target_host}...")

        cmd = [
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            target_host, 'apt list --upgradable 2>/dev/null'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'linux-image-' in line and 'generic' in line:
                    print("    Found kernel update available")
                    return _STATUS_UPDATE_AVAILABLE
                elif 'raspberrypi-kernel' in line:
                    print("    Found kernel update available")
                    return _STATUS_UPDATE_AVAILABLE
                elif 'linux-image-rpi-' in line:
                    print("    Found kernel update available")
                    new_version = _get_rpi_new_kernel_version(target_host)
                    return new_version if new_version else _STATUS_UPDATE_AVAILABLE

            return _STATUS_NO_UPDATE

        return _STATUS_NO_UPDATE

    except Exception as e:
        print(f"  Error getting kernel updates via SSH: {e}")
        return _STATUS_NO_UPDATE


def _get_rpi_new_kernel_version(target_host):
    """Extract actual new RPi kernel version from apt-cache show."""
    try:
        cmd = [
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            target_host,
            'apt-cache show linux-image-rpi-v8 2>/dev/null | grep "^Depends" | head -1'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and result.stdout:
            # Depends: linux-image-6.12.75+rpt-rpi-v8, kmod, linux-base (>= 4.3~)
            match = re.search(r'linux-image-(\d[^,\s]+)', result.stdout)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None
