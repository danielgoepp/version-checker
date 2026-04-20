#!/usr/bin/env python

import subprocess
import re

_STATUS_NO_UPDATE = 'no update'
_STATUS_UPDATE_AVAILABLE = 'update available'


def get_latest_linux_kernel_version(current_kernel, target_host):
    if not target_host:
        return _STATUS_NO_UPDATE
    try:
        return check_for_kernel_updates(target_host, current_kernel)
    except Exception as e:
        print(f"  Error checking kernel versions: {e}")
        return _STATUS_NO_UPDATE


def check_for_kernel_updates(target_host, current_kernel=''):
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
                    new_version = _get_new_kernel_version(target_host, 'linux-image-generic')
                    return new_version if new_version else _STATUS_UPDATE_AVAILABLE
                elif 'raspberrypi-kernel' in line:
                    print("    Found kernel update available")
                    return _STATUS_UPDATE_AVAILABLE
                elif 'linux-image-rpi-' in line:
                    print("    Found kernel update available")
                    meta_package = _rpi_meta_package(current_kernel)
                    new_version = _get_new_kernel_version(target_host, meta_package)
                    return new_version if new_version else _STATUS_UPDATE_AVAILABLE

            return _STATUS_NO_UPDATE

        return _STATUS_NO_UPDATE

    except Exception as e:
        print(f"  Error getting kernel updates via SSH: {e}")
        return _STATUS_NO_UPDATE


def _rpi_meta_package(current_kernel):
    if 'rpi-2712' in current_kernel:
        return 'linux-image-rpi-2712'
    return 'linux-image-rpi-v8'


def _get_new_kernel_version(target_host, meta_package):
    try:
        cmd = [
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            target_host,
            f'apt-cache show {meta_package} 2>/dev/null | grep "^Depends" | head -1'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and result.stdout:
            match = re.search(r'linux-image-(\d[^,\s]+)', result.stdout)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None
