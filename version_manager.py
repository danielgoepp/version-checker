#!/usr/bin/env python

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import json
import sys
import threading
import urllib3
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

from src import db

from src.checkers.github import get_github_latest_version, get_github_latest_tag
from src.checkers.home_assistant import get_home_assistant_version
from src.checkers.esphome import get_esphome_version
from src.checkers.music_assistant import get_music_assistant_version
from src.checkers.ble_proxy import get_ble_proxy_version
from src.checkers.konnected import get_konnected_version, get_konnected_current_version
from src.checkers.airgradient import (
    get_airgradient_version,
    get_airgradient_current_version,
)
from src.checkers.opnsense import get_opnsense_version
from src.checkers.k3s import get_k3s_current_version
from src.checkers.linux_kernel import is_kernel_only_update
from src.checkers.zigbee2mqtt import get_zigbee2mqtt_version
from src.checkers.kopia import get_kopia_version
from src.checkers.kubectl import (
    get_telegraf_version,
    get_mosquitto_version,
    get_victoriametrics_version,
    get_calico_version,
    get_metallb_version,
    get_alertmanager_version,
    get_fluentbit_version,
    get_mongodb_version,
    get_opensearch_version,
    get_pgadmin_version,
    get_unpoller_version,
    get_certmanager_version,
    get_postfix_version,
    get_garage_version,
)
from src.checkers.cnpg import get_cnpg_version, get_cnpg_postgres_latest_version
from src.checkers.server_status import check_server_status
from src.checkers.proxmox import get_proxmox_version, get_proxmox_latest_version
from src.checkers.tailscale import check_tailscale_versions
from src.checkers.traefik import get_traefik_version
from src.checkers.graylog import (
    get_graylog_current_version,
    get_graylog_latest_version_from_repo,
    get_postgresql_latest_version_from_ghcr,
)
from src.checkers.grafana import get_grafana_version
from src.checkers.mongodb import get_mongodb_latest_version
from src.checkers.unifi_network import (
    get_ui_network_version,
    get_unifi_network_latest_version,
    get_unifi_os_server_latest_version,
)
from src.checkers.syncthing import check_syncthing_current_version
from src.checkers.awx import check_awx_current_version
from src.checkers.graylog_compat import get_opensearch_compatible_version
from src.checkers.dockerhub import (
    get_dockerhub_latest_version,
    get_dockerhub_latest_beta,
    clear_cache as dockerhub_clear_cache,
)
from src.checkers.n8n import get_n8n_version_kubectl
from src.checkers.openclaw import get_openclaw_version
from src.checkers.wyoming import get_rhasspy_version, get_wyoming_satellite_version
from src.checkers.ollama import get_ollama_version
from src.checkers.docker import get_docker_version
from src.checkers.portainer import get_portainer_version
from src.checkers.open_webui import get_open_webui_version
from src.checkers.vault import get_vault_version
from src.checkers.uptime_kuma import get_uptime_kuma_version
from src.checkers.upgrade import trigger_awx_upgrade, trigger_awx_apt_upgrade, trigger_awx_llm_upgrade, trigger_awx_esphome_upgrade, trigger_awx_calico_upgrade, trigger_awx_uos_upgrade, trigger_vault_upgrade_workflow, update_manifest_version, update_helm_values_version, git_commit_push_manifest, kubectl_apply_manifest, AWX_UPGRADE_METHODS, MANIFEST_UPGRADE_METHODS, HELM_UPGRADE_METHODS, CR_UPGRADE_METHODS
import config


FIELD_MAP = {
    "Name": "name",
    "Enabled": "enabled",
    "Context": "context",
    "Namespace": "namespace",
    "Instance": "instance",
    "Type": "type",
    "Category": "category",
    "Version_Pin": "version_pin",
    "Upgrade": "upgrade",
    "Target": "target",
    "Esphome_Key": "esphome_key",
    "GitHub": "github",
    "DockerHub": "dockerhub",
    "Current_Version": "current_version",
    "Latest_Version": "latest_version",
    "Status": "status",
    "Last_Checked": "last_checked",
    "Last_Upgraded": "last_upgraded",
    "Check_Current": "check_current",
    "Check_Latest": "check_latest",
    "Helm_Values_File": "helm_values_file",
    "Extra_Manifests": "extra_manifests",
    "Library_GitHub": "library_github",
    "Current_Library_Version": "current_library_version",
    "Latest_Library_Version": "latest_library_version",
    "Notes": "notes",
}
YAML_TO_FIELD = {v: k for k, v in FIELD_MAP.items()}

# Columns with non-string storage representations that need conversion
# between the DB row and the in-memory frontmatter dict.
_BOOL_COLUMNS = {"enabled"}
_JSON_COLUMNS = {"extra_manifests"}


def _row_to_frontmatter(row) -> dict:
    fm = {}
    for col in row.keys():
        value = row[col]
        if col == "id":
            continue
        if col in _BOOL_COLUMNS:
            value = bool(value)
        elif col in _JSON_COLUMNS:
            value = json.loads(value) if value else []
        fm[col] = value
    return fm


def _frontmatter_value_to_db(col: str, value):
    if col in _BOOL_COLUMNS:
        return int(bool(value))
    if col in _JSON_COLUMNS:
        return json.dumps(value) if value else None
    return value


def format_version(version, library_version=None, empty="N/A"):
    """Version string for display, with the ESPHome library version appended
    when the app tracks one — otherwise a bare `2026.6.5 -> 2026.6.5` line can
    show "Update Available" with no visible difference."""
    display = version if version else empty
    return f"{display} (lib {library_version})" if library_version else display


def _kubectl_checker(func):
    """Adapt f(instance, context=, namespace=) to an app_data dict."""
    return lambda a: func(a["Instance"], context=a["Context"] or None, namespace=a["Namespace"] or None)


def _api_checker(func):
    """Adapt f(instance, url) to an app_data dict."""
    return lambda a: func(a["Instance"], a["Target"])


def _esphome_checker(a):
    return get_ble_proxy_version(a["Instance"], a["Target"], a["Esphome_Key"])


def _tailscale_checker(a):
    print("  Checking all Tailscale devices...")
    results = check_tailscale_versions(
        api_key=config.TAILSCALE_ACCESS_TOKEN, tailnet=config.TAILSCALE_TAILNET
    )
    if not results or results["total_devices"] == 0:
        return None
    return {
        "current_version": f"{results['devices_needing_updates']} need updates",
        "latest_version": f"{results['devices_up_to_date']} up-to-date",
    }


# Current-version dispatch: one entry per application name; each checker takes
# the PascalCase app_data dict and returns a version string, a dict (normalized
# in get_current_version), or None. ssh/ssh_apt rows are dispatched by method
# instead — their names describe host classes (rpi, ubuntu, ...), not one app.
CURRENT_CHECKERS = {
    # HTTP/API
    "homeassistant": _api_checker(get_home_assistant_version),
    "esphome": lambda a: get_esphome_version(a["Target"]),
    "ble-proxy": _esphome_checker,
    "co2": _esphome_checker,
    "m5-echo": _esphome_checker,
    "esp-heat-control": _esphome_checker,
    "konnected": lambda a: get_konnected_current_version(a["Instance"], a["Target"], a["Esphome_Key"]),
    "airgradient": lambda a: get_airgradient_current_version(a["Instance"], a["Target"], a["Esphome_Key"]),
    "traefik": _api_checker(get_traefik_version),
    "opnsense": _api_checker(get_opnsense_version),
    "proxmox": _api_checker(get_proxmox_version),
    "tailscale": _tailscale_checker,
    "graylog": _api_checker(get_graylog_current_version),
    "ui-network": _api_checker(get_ui_network_version),
    "awx": _api_checker(check_awx_current_version),
    "syncthing": _api_checker(check_syncthing_current_version),
    "ollama": _api_checker(get_ollama_version),
    "portainer": _api_checker(get_portainer_version),
    "openwebui": _api_checker(get_open_webui_version),
    "uptime-kuma": _api_checker(get_uptime_kuma_version),
    "music-assistant": _api_checker(get_music_assistant_version),
    # kubectl
    "telegraf": _kubectl_checker(get_telegraf_version),
    "victoriametrics": _kubectl_checker(get_victoriametrics_version),
    "mosquitto": _kubectl_checker(get_mosquitto_version),
    "calico": _kubectl_checker(get_calico_version),
    "metallb": _kubectl_checker(get_metallb_version),
    "alertmanager": _kubectl_checker(get_alertmanager_version),
    "fluent-bit": _kubectl_checker(get_fluentbit_version),
    "mongodb": _kubectl_checker(get_mongodb_version),
    "opensearch": _kubectl_checker(get_opensearch_version),
    "cnpg": _kubectl_checker(get_cnpg_version),
    "pgadmin": _kubectl_checker(get_pgadmin_version),
    "grafana": _kubectl_checker(get_grafana_version),
    "unpoller": _kubectl_checker(get_unpoller_version),
    "cert-manager": _kubectl_checker(get_certmanager_version),
    "postfix": _kubectl_checker(get_postfix_version),
    "garage": _kubectl_checker(get_garage_version),
    "n8n": _kubectl_checker(get_n8n_version_kubectl),
    "openclaw": _kubectl_checker(get_openclaw_version),
    "vault": _kubectl_checker(get_vault_version),
    "k3s": lambda a: get_k3s_current_version(a["Instance"], context=a["Context"] or None),
    "rhasspy": _api_checker(get_rhasspy_version),
    # MQTT
    "zigbee2mqtt": lambda a: get_zigbee2mqtt_version(a["Instance"]),
    # local commands / SSH
    "kopia": _api_checker(get_kopia_version),
    "docker": _api_checker(get_docker_version),
    "wyoming-satellite": _api_checker(get_wyoming_satellite_version),
}


class VersionManager:
    STATUS_ICONS = {
        "Up to Date": "✅",
        "Update Available": "⚠️ ",
        "Latest Available": "📋",
        "Current Version": "📌",
        "Unknown": "❓",
    }

    DEFAULT_DB_PATH = Path(
        getattr(config, "DATABASE_PATH", str(Path(__file__).parent / "data" / "version_checker.db"))
    )

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else self.DEFAULT_DB_PATH
        self.conn = db.get_connection(self.db_path)
        db.init_db(self.conn)
        self.notes = []
        self._db_lock = threading.Lock()
        self.load_data()

    def load_data(self):
        rows = self.conn.execute(
            "SELECT * FROM applications ORDER BY name, instance"
        ).fetchall()
        self.notes = [{"id": row["id"], "frontmatter": _row_to_frontmatter(row)} for row in rows]
        enabled = sum(1 for n in self.notes if n["frontmatter"].get("enabled", True) is True)
        print(f"Loaded {len(self.notes)} applications from database ({enabled} enabled)")

    def save_workbook(self):
        pass

    def log_transaction(self, idx: int, upgrade_method: str, from_version: str, to_version: str, detail: str = "") -> None:
        fm = self.notes[idx]["frontmatter"]
        self.conn.execute(
            "INSERT INTO transactions (application_id, name, instance, upgrade_method, from_version, to_version, timestamp, detail) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                self.notes[idx]["id"],
                fm.get("name", ""),
                fm.get("instance", ""),
                upgrade_method,
                from_version,
                to_version,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                detail,
            ),
        )
        self.conn.commit()

    def get_transaction_history(
        self, limit: int | None = 40, name: str = "", instance: str = "", fuzzy_name: bool = False
    ) -> list[dict]:
        """Most recent transactions first, capped at `limit`.

        `name`/`instance` match exactly (case-insensitive) unless `fuzzy_name`
        is set, in which case `name` is a substring match — used by the TUI's
        live filter box, where typing a partial app name should narrow results
        immediately rather than requiring the full exact name.
        """
        query = (
            "SELECT name, instance, upgrade_method, from_version, to_version, timestamp, detail "
            "FROM transactions"
        )
        conditions = []
        params: list = []
        if name:
            if fuzzy_name:
                conditions.append("name LIKE ?")
                params.append(f"%{name}%")
            else:
                conditions.append("LOWER(name) = LOWER(?)")
                params.append(name)
        if instance:
            conditions.append("LOWER(instance) = LOWER(?)")
            params.append(instance)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_row_data(self, idx: int) -> dict:
        fm = self.notes[idx]["frontmatter"]
        data = {}
        for yaml_key, pascal_key in YAML_TO_FIELD.items():
            val = fm.get(yaml_key)
            data[pascal_key] = val if val is not None else ""
        return data

    def update_row_data(self, idx: int, updates: dict) -> None:
        fm = self.notes[idx]["frontmatter"]
        changed_columns = {}
        for pascal_key, value in updates.items():
            column = FIELD_MAP.get(pascal_key)
            if column:
                fm[column] = value if value != "" else None
                changed_columns[column] = fm[column]

        if not changed_columns:
            return

        set_clause = ", ".join(f"{col} = ?" for col in changed_columns)
        values = [_frontmatter_value_to_db(col, val) for col, val in changed_columns.items()]
        values.append(self.notes[idx]["id"])
        with self._db_lock:
            self.conn.execute(f"UPDATE applications SET {set_clause} WHERE id = ?", values)
            self.conn.commit()

    def find_application_row(self, app_name: str, instance: str = "prod") -> int | None:
        for idx, note in enumerate(self.notes):
            fm = note["frontmatter"]
            if (
                str(fm.get("name", "")).lower() == app_name.lower()
                and str(fm.get("instance", "")).lower() == instance.lower()
            ):
                return idx
        return None

    def find_application_rows_by_name(self, app_name: str, instance: str = "") -> list[int]:
        matches = []
        for idx, note in enumerate(self.notes):
            fm = note["frontmatter"]
            if fm.get("enabled", True) is not True:
                continue
            if str(fm.get("name", "")).lower() != app_name.lower():
                continue
            if instance and str(fm.get("instance", "")).lower() != instance.lower():
                continue
            matches.append(idx)
        return matches

    def get_all_application_names(self) -> list[str]:
        names = set()
        for note in self.notes:
            fm = note["frontmatter"]
            if fm.get("enabled", True) is not True:
                continue
            if fm.get("name"):
                names.add(fm["name"])
        return sorted(names)

    def _get_dockerhub_version_for_app(self, app_name, dockerhub_repo, version_pin=None):
        if version_pin == "beta":
            return get_dockerhub_latest_beta(dockerhub_repo)
        if app_name == "mongodb":
            return get_mongodb_latest_version()
        elif app_name == "graylog":
            if "graylog" in dockerhub_repo.lower():
                return get_graylog_latest_version_from_repo(dockerhub_repo)
            elif "postgres" in dockerhub_repo.lower():
                return get_postgresql_latest_version_from_ghcr(dockerhub_repo)
            else:
                return get_dockerhub_latest_version(dockerhub_repo)
        else:
            return get_dockerhub_latest_version(dockerhub_repo)

    def _get_github_version_for_app(self, app_name, github_repo, check_latest):
        if app_name == "mongodb" and github_repo == "mongodb/mongo":
            return get_mongodb_latest_version()
        elif check_latest == "github_release":
            return get_github_latest_version(github_repo)
        elif check_latest == "github_tag":
            return get_github_latest_tag(github_repo)
        return None

    def get_latest_version(self, app_name, check_latest, github_repo, dockerhub_repo, version_pin=None):
        latest_version = None

        if check_latest == "github_release" or check_latest == "github_tag":
            if github_repo and github_repo.strip():
                latest_version = self._get_github_version_for_app(
                    app_name, github_repo, check_latest
                )
        elif check_latest == "docker_hub":
            if dockerhub_repo and dockerhub_repo.strip():
                if app_name == "cnpg" and "postgres-containers" in dockerhub_repo:
                    latest_version = get_cnpg_postgres_latest_version()
                else:
                    latest_version = self._get_dockerhub_version_for_app(
                        app_name, dockerhub_repo, version_pin
                    )
        elif check_latest == "proxmox":
            latest_version = get_proxmox_latest_version(include_ceph=True)
        elif check_latest == "unifi_network":
            if app_name == "ui-network":
                latest_version = get_unifi_network_latest_version()
        elif check_latest == "unifi_os_server":
            latest_version = get_unifi_os_server_latest_version()
        elif check_latest == "graylog_compat":
            latest_version = get_opensearch_compatible_version()
        elif check_latest == "helm_search":
            if github_repo and github_repo.strip():
                from src.checkers.utils import get_helm_search_app_version
                latest_version = get_helm_search_app_version(github_repo, app_name)
        elif check_latest == "helm_chart":
            if app_name == "mongodb":
                from src.checkers.utils import get_helm_chart_version
                latest_version = get_helm_chart_version(
                    "mongodb/helm-charts", "community-operator", "operator.version"
                )
            elif app_name == "fluent-bit":
                from src.checkers.utils import get_helm_chart_app_version
                latest_version = get_helm_chart_app_version(
                    "fluent/helm-charts", "fluent-bit"
                )

        return latest_version

    def get_current_version(self, app_data):
        app_name = app_data.get("Name", "")

        checker = CURRENT_CHECKERS.get(app_name)
        if checker is not None:
            result = checker(app_data)
        elif app_data.get("Check_Current") == "ssh" and app_data.get("Check_Latest") == "ssh_apt":
            result = check_server_status(app_data.get("Instance", ""), app_data.get("Target", ""))
        else:
            result = None

        current_version = None
        latest_version = None
        firmware_update_available = False
        library_current_version = None

        if isinstance(result, dict):
            current_version = result.get("current_version") or result.get("esphome_version")
            latest_version = result.get("full_version") or result.get("latest_version")
            firmware_update_available = result.get("firmware_update_available", False)
            library_current_version = result.get("library_version")
        else:
            current_version = result

        return current_version, latest_version, firmware_update_available, library_current_version

    def check_single_application(self, idx: int, verbose: bool = True):
        app_data = self.get_row_data(idx)
        app_name = app_data.get("Name", "")
        instance = app_data.get("Instance", "prod")
        check_current = app_data.get("Check_Current", "")
        check_latest = app_data.get("Check_Latest", "")
        github_repo = app_data.get("GitHub", "")
        dockerhub_repo = app_data.get("DockerHub", "")
        library_github = app_data.get("Library_GitHub", "")

        if verbose:
            print(f"Checking {app_name} ({instance})...")

        version_pin = app_data.get("Version_Pin", "")
        latest_version = self.get_latest_version(
            app_name, check_latest, github_repo, dockerhub_repo, version_pin
        )
        current_version, ssh_latest_version, firmware_update_available, library_current_version = (
            self.get_current_version(app_data)
        )

        if ssh_latest_version:
            latest_version = ssh_latest_version

        library_latest_version = None
        if library_github and library_github.strip():
            if app_name == "konnected":
                library_latest_version = get_konnected_version(instance, None, library_github)
            elif app_name == "airgradient":
                library_latest_version = get_airgradient_version(instance, None, library_github)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updates = {"Last_Checked": timestamp}
        updates["Current_Version"] = current_version if current_version else ""
        updates["Latest_Version"] = latest_version if latest_version else ""

        if library_current_version is not None or library_latest_version is not None:
            updates["Current_Library_Version"] = library_current_version if library_current_version else ""
            updates["Latest_Library_Version"] = library_latest_version if library_latest_version else ""

        if firmware_update_available:
            updates["Notes"] = "Firmware update available"
        elif app_data.get("Notes", "") == "Firmware update available":
            # Only clear the note this code itself wrote, never free-text notes.
            updates["Notes"] = ""

        status = "Unknown"
        if current_version and latest_version:
            if check_current == "api" and app_name == "tailscale":
                if "0 need updates" in current_version:
                    status = "Up to Date"
                else:
                    status = "Update Available"
            elif check_current == "ssh" and check_latest == "ssh_apt":
                if latest_version == "No updates":
                    status = "Up to Date"
                else:
                    status = "Update Available"
            else:
                current_clean = current_version
                if "build:" in current_version:
                    current_clean = current_version.split("build:")[0].strip()

                latest_clean = latest_version
                if latest_clean.startswith("v"):
                    latest_clean = latest_clean[1:]

                if current_clean == latest_clean:
                    status = "Up to Date"
                else:
                    status = "Update Available"
        elif latest_version and not current_version:
            status = "Latest Available"
        elif current_version and not latest_version:
            status = "Current Version"

        if status == "Up to Date" and library_current_version and library_latest_version:
            if library_current_version != library_latest_version:
                status = "Update Available"

        updates["Status"] = status
        self.update_row_data(idx, updates)

        current_display = current_version if current_version else "N/A"
        latest_display = latest_version if latest_version else "N/A"
        icon = self.STATUS_ICONS.get(status, "")

        if verbose:
            print(f"  Current: {current_display}")
            print(f"  Latest: {latest_display}")
            if library_current_version or library_latest_version:
                lib_current_display = library_current_version if library_current_version else "N/A"
                lib_latest_display = library_latest_version if library_latest_version else "N/A"
                print(f"  Library Current: {lib_current_display}")
                print(f"  Library Latest: {lib_latest_display}")
            print(f"  Status: {icon} {status}")
            print()
        else:
            current_display = format_version(current_version, library_current_version)
            latest_display = format_version(latest_version, library_latest_version)
            print(f"{icon} {app_name} ({instance}): {current_display} -> {latest_display} ({status})")

        return f"{app_name} ({instance})" if not current_version else None

    def check_all_applications(self, max_workers: int = 8, verbose: bool = False):
        """Check versions for all enabled applications concurrently.

        Each app's output (including any nested prints from checker modules,
        e.g. zigbee2mqtt's MQTT wait) is buffered per-thread and flushed as a
        single atomic write, so concurrent checks can't interleave mid-line.
        """
        print("Starting version check for all applications...")
        print("=" * 50)

        # The GitHub/Docker Hub lookups are lru_cached to dedupe multi-instance
        # apps within one run; clear them here so the cache scopes to the run,
        # not the process — otherwise a long-lived TUI session keeps serving
        # the latest-version results from its first check-all forever.
        get_github_latest_version.cache_clear()
        get_github_latest_tag.cache_clear()
        dockerhub_clear_cache()

        enabled_indices = []
        skipped = 0
        for idx, note in enumerate(self.notes):
            if note["frontmatter"].get("enabled", True) is True:
                enabled_indices.append(idx)
            else:
                skipped += 1

        total_apps = len(enabled_indices)
        if skipped > 0:
            print(f"Skipping {skipped} disabled applications")
        print(f"Checking {total_apps} enabled applications ({max_workers} workers)...")
        print()

        unavailable = []
        completed = 0

        _thread_local = threading.local()
        _real_stdout = sys.stdout
        _write_lock = threading.Lock()

        class _ThreadBufferedStdout:
            def write(self, text):
                buf = getattr(_thread_local, "buffer", None)
                if buf is not None:
                    buf.write(text)
                else:
                    _real_stdout.write(text)

            def flush(self):
                _real_stdout.flush()

        def _run_one(idx):
            _thread_local.buffer = io.StringIO()
            try:
                label = self.check_single_application(idx, verbose=verbose)
                return idx, _thread_local.buffer.getvalue(), label, None
            except Exception as e:
                return idx, _thread_local.buffer.getvalue(), None, e
            finally:
                _thread_local.buffer = None

        sys.stdout = _ThreadBufferedStdout()
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(_run_one, idx) for idx in enabled_indices]
                for future in as_completed(futures):
                    idx, output, label, error = future.result()
                    completed += 1
                    with _write_lock:
                        if verbose:
                            if output:
                                _real_stdout.write(output)
                                if not output.endswith("\n"):
                                    _real_stdout.write("\n")
                        elif not error:
                            # Nested checker calls (kubectl lookups, apt/proxmox status
                            # lines, etc.) print their own chatter into the buffer ahead
                            # of check_single_application's own final summary line —
                            # only that last line belongs in condensed output.
                            lines = [l for l in output.splitlines() if l.strip()]
                            summary = lines[-1] if lines else ""
                            _real_stdout.write(f"[{completed}/{total_apps}] {summary}\n")
                        if error:
                            app_data = self.get_row_data(idx)
                            prefix = f"[{completed}/{total_apps}] " if not verbose else ""
                            _real_stdout.write(
                                f"{prefix}  Error checking {app_data.get('Name', '')} "
                                f"({app_data.get('Instance', '')}): {error}\n"
                            )
                    if label:
                        unavailable.append(label)
        finally:
            sys.stdout = _real_stdout

        print("=" * 50)
        print(f"Version check completed! Checked {total_apps} applications.")

        if unavailable:
            print(f"\n❓ Current version unavailable for {len(unavailable)} application(s):")
            for label in unavailable:
                print(f"  {label}")

    def show_summary(self):
        print("\nVersion Summary (Enabled Applications):")
        print("=" * 40)

        status_counts = {}
        total_apps = 0
        disabled_apps = 0

        for note in self.notes:
            fm = note["frontmatter"]
            if fm.get("enabled", True) is not True:
                disabled_apps += 1
                continue
            status = fm.get("status") or "Unknown"
            status_counts[status] = status_counts.get(status, 0) + 1
            total_apps += 1

        for status, count in status_counts.items():
            icon = self.STATUS_ICONS.get(status, "")
            print(f"{icon} {status}: {count}")

        print(f"\nTotal Enabled Applications: {total_apps}")
        if disabled_apps > 0:
            print(f"Disabled Applications: {disabled_apps}")

        print(f"\n⚠️  Applications needing updates:")
        for note in self.notes:
            fm = note["frontmatter"]
            if fm.get("enabled", True) is not True:
                continue
            if fm.get("status") != "Update Available":
                continue
            name = fm.get("name", "")
            instance = fm.get("instance", "")
            current = format_version(fm.get("current_version"), fm.get("current_library_version"))
            latest = format_version(fm.get("latest_version"), fm.get("latest_library_version"))
            app_display = f"{name}-{instance}" if instance != "prod" else name
            print(f"  {app_display}: {current} -> {latest}")

    def show_applications(self):
        all_data = []
        max_widths = {
            "index": 4,
            "name": len("Name"),
            "instance": len("Instance"),
            "current": len("Current"),
            "latest": len("Latest"),
            "status": 3,
        }

        for note in self.notes:
            fm = note["frontmatter"]
            if fm.get("enabled", True) is not True:
                continue

            name = str(fm.get("name", ""))
            instance = str(fm.get("instance", ""))
            current = format_version(fm.get("current_version"), fm.get("current_library_version"), empty="")
            latest = format_version(fm.get("latest_version"), fm.get("latest_library_version"), empty="")
            status = str(fm.get("status", "") or "")

            max_widths["name"] = max(max_widths["name"], len(name))
            max_widths["instance"] = max(max_widths["instance"], len(instance))
            max_widths["current"] = max(max_widths["current"], len(current))
            max_widths["latest"] = max(max_widths["latest"], len(latest))

            all_data.append({"name": name, "instance": instance, "current": current, "latest": latest, "status": status})

        total_width = sum(max_widths.values()) + len(max_widths) * 2

        print("\nApplications:")
        print("=" * total_width)
        print(
            f"{'#':<{max_widths['index']}} {'Name':<{max_widths['name']}} {'Instance':<{max_widths['instance']}} {'Current':<{max_widths['current']}} {'Latest':<{max_widths['latest']}} {'':<{max_widths['status']}}"
        )
        print("-" * total_width)

        for index, data in enumerate(all_data):
            status_icon = self.STATUS_ICONS.get(data["status"], "") if data["status"] else ""
            print(
                f"{index:<{max_widths['index']}} {data['name']:<{max_widths['name']}} {data['instance']:<{max_widths['instance']}} {data['current']:<{max_widths['current']}} {data['latest']:<{max_widths['latest']}} {status_icon:<{max_widths['status']}}"
            )

        print(f"\nTotal: {len(all_data)} applications")

    def show_updates(self):
        updates = []
        max_widths = {
            "name": len("Name"),
            "instance": len("Instance"),
            "current": len("Current"),
            "latest": len("Latest"),
            "status": 3,
        }

        for note in self.notes:
            fm = note["frontmatter"]
            if fm.get("enabled", True) is not True:
                continue
            if fm.get("status") != "Update Available":
                continue

            name = str(fm.get("name", ""))
            instance = str(fm.get("instance", ""))
            current = format_version(fm.get("current_version"), fm.get("current_library_version"), empty="")
            latest = format_version(fm.get("latest_version"), fm.get("latest_library_version"), empty="")

            max_widths["name"] = max(max_widths["name"], len(name))
            max_widths["instance"] = max(max_widths["instance"], len(instance))
            max_widths["current"] = max(max_widths["current"], len(current))
            max_widths["latest"] = max(max_widths["latest"], len(latest))

            updates.append({"name": name, "instance": instance, "current": current, "latest": latest, "status": "Update Available"})

        total_width = sum(max_widths.values()) + len(max_widths) * 2

        print("\nApplications Needing Updates:")
        print("=" * total_width)
        print(
            f"{'Name':<{max_widths['name']}} {'Instance':<{max_widths['instance']}} {'Current':<{max_widths['current']}} {'Latest':<{max_widths['latest']}} {'':<{max_widths['status']}}"
        )
        print("-" * total_width)

        for data in updates:
            status_icon = self.STATUS_ICONS.get(data["status"], "")
            print(
                f"{data['name']:<{max_widths['name']}} {data['instance']:<{max_widths['instance']}} {data['current']:<{max_widths['current']}} {data['latest']:<{max_widths['latest']}} {status_icon:<{max_widths['status']}}"
            )

        print(f"\nTotal: {len(updates)} applications")

    def show_history(self, name: str = "", instance: str = "", limit: int | None = 40):
        history = self.get_transaction_history(limit=limit, name=name, instance=instance)

        max_widths = {
            "timestamp": len("Timestamp"),
            "name": len("Name"),
            "instance": len("Instance"),
            "method": len("Method"),
            "from": len("From"),
            "to": len("To"),
        }

        rows = []
        for tx in history:
            row = {
                "timestamp": tx["timestamp"],
                "name": tx["name"],
                "instance": tx["instance"],
                "method": tx["upgrade_method"] or "",
                "from": tx["from_version"] or "",
                "to": tx["to_version"] or "",
                "detail": tx["detail"] or "",
            }
            for key in max_widths:
                max_widths[key] = max(max_widths[key], len(str(row[key])))
            rows.append(row)

        total_width = sum(max_widths.values()) + len(max_widths) * 2

        print("\nUpgrade History:")
        print("=" * total_width)
        print(
            f"{'Timestamp':<{max_widths['timestamp']}} {'Name':<{max_widths['name']}} {'Instance':<{max_widths['instance']}} {'Method':<{max_widths['method']}} {'From':<{max_widths['from']}} {'To':<{max_widths['to']}}"
        )
        print("-" * total_width)
        for row in rows:
            line = (
                f"{row['timestamp']:<{max_widths['timestamp']}} {row['name']:<{max_widths['name']}} "
                f"{row['instance']:<{max_widths['instance']}} {row['method']:<{max_widths['method']}} "
                f"{row['from']:<{max_widths['from']}} {row['to']:<{max_widths['to']}}"
            )
            if row["detail"]:
                line += f"  {row['detail']}"
            print(line)

        cap_note = f" (capped at {limit})" if limit else ""
        print(f"\nShowing {len(rows)} transaction(s){cap_note}")

    def upgrade_application(self, app_name: str, dry_run: bool = False, instance: str = "", force: bool = False):
        matching = self.find_application_rows_by_name(app_name, instance=instance)

        if not matching:
            print(f"Application '{app_name}' not found")
            return

        self.upgrade_rows(matching, dry_run=dry_run, force=force)

    def _record_upgrade(self, idx: int, upgrade_method: str, dry_run: bool, detail: str = "") -> None:
        if dry_run:
            return
        app_data = self.get_row_data(idx)
        self.update_row_data(idx, {"Last_Upgraded": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        self.log_transaction(
            idx,
            upgrade_method,
            app_data.get("Current_Version", "") or "",
            app_data.get("Latest_Version", "") or "",
            detail=detail,
        )

    def upgrade_rows(self, indices: list[int], dry_run: bool = False, force: bool = False):
        """Upgrade a set of rows as one run.

        Run-scoped state lives here so cross-instance dedup works no matter how
        the rows were selected (CLI name lookup or TUI multi-select): vault's
        shared workflow fires once *after* every instance's values update has
        been pushed, and an ansible-esphome app whose every enabled instance is
        in the run gets a single base-pattern AWX job instead of one per device.
        """
        launched = 0
        manifests_updated = 0
        skipped = 0
        # Vault instances (server + vault-k8s injector) share one Helm release
        # and values file — collect them and fire the workflow once at the end,
        # after all their values updates have been committed.
        vault_pending: list[int] = []
        esphome_fired: set[str] = set()

        for idx in indices:
            app_data = self.get_row_data(idx)
            app_name = app_data.get("Name", "")
            instance = app_data.get("Instance", "prod")
            version_pin = app_data.get("Version_Pin", "") or ""
            upgrade_method = app_data.get("Upgrade", "") or ""
            status = app_data.get("Status", "") or ""
            label = f"{app_name} ({instance})"

            if self.notes[idx]["frontmatter"].get("enabled", True) is not True:
                print(f"  Skipping {label}: disabled")
                skipped += 1
                continue

            if not force and status == "Up to Date":
                print(f"  Skipping {label}: already up to date")
                skipped += 1
                continue

            if upgrade_method == "ansible-apt":
                category = app_data.get("Category", "") or ""
                latest = app_data.get("Latest_Version", "") or ""
                if not force and category == "Kubernetes" and is_kernel_only_update(latest):
                    print(f"  Skipping {label}: only a kernel update pending (k3s servers reboot for kernels via separate orchestration)")
                    skipped += 1
                    continue
                print(f"  Upgrading {label} via AWX (method: {upgrade_method})...")
                if trigger_awx_apt_upgrade(instance, instance, dry_run=dry_run):
                    launched += 1
                    self._record_upgrade(idx, "ansible-apt", dry_run)
                else:
                    skipped += 1
                continue

            if upgrade_method == "ansible-llm":
                print(f"  Upgrading {label} via AWX (method: {upgrade_method})...")
                if trigger_awx_llm_upgrade(app_name, instance, dry_run=dry_run):
                    launched += 1
                    self._record_upgrade(idx, "ansible-llm", dry_run)
                else:
                    skipped += 1
                continue

            if upgrade_method == "ansible-esphome":
                if app_name in esphome_fired:
                    print(f"  Skipping {label}: ESPHome AWX job already launched for all instances")
                    self._record_upgrade(idx, "ansible-esphome", dry_run, detail="covered by shared ESPHome AWX job")
                    skipped += 1
                    continue
                esphome_target_map = {"konnected": "garage-door-opener", "esp-heat-control": "heat-control"}
                base_target = esphome_target_map.get(app_name, app_name)
                covers_all = set(self.find_application_rows_by_name(app_name)) <= set(indices)
                if covers_all:
                    esphome_target = base_target
                    print(f"  Upgrading all {app_name} devices via AWX (method: {upgrade_method})...")
                else:
                    esphome_target = f"{base_target}-{instance}"
                    print(f"  Upgrading {label} via AWX (method: {upgrade_method})...")
                if trigger_awx_esphome_upgrade(esphome_target, instance, dry_run=dry_run):
                    launched += 1
                    self._record_upgrade(idx, "ansible-esphome", dry_run)
                    if covers_all:
                        esphome_fired.add(app_name)
                else:
                    skipped += 1
                continue

            if upgrade_method == "ansible-calico":
                latest_version = app_data.get("Latest_Version", "") or ""
                if not latest_version:
                    print(f"  Skipping {label}: no latest version known")
                    skipped += 1
                    continue
                target_version = latest_version if latest_version.startswith("v") else f"v{latest_version}"
                print(f"  Upgrading {label} via AWX (method: {upgrade_method})...")
                if trigger_awx_calico_upgrade(target_version, instance, dry_run=dry_run):
                    launched += 1
                    self._record_upgrade(idx, "ansible-calico", dry_run)
                else:
                    skipped += 1
                continue

            if upgrade_method == "ansible-uos":
                print(f"  Upgrading {label} via AWX (method: {upgrade_method})...")
                if trigger_awx_uos_upgrade(instance, dry_run=dry_run):
                    launched += 1
                    self._record_upgrade(idx, "ansible-uos", dry_run)
                else:
                    skipped += 1
                continue

            if version_pin == "latest":
                if upgrade_method not in AWX_UPGRADE_METHODS:
                    print(f"  Skipping {label}: upgrade method '{upgrade_method}' is not supported")
                    skipped += 1
                    continue
                print(f"  Upgrading {label} via AWX (method: {upgrade_method})...")
                if trigger_awx_upgrade(f"{app_name}-{instance}", instance, dry_run=dry_run):
                    launched += 1
                    self._record_upgrade(idx, upgrade_method, dry_run)
                else:
                    skipped += 1
                continue

            if version_pin == "pinned":
                if upgrade_method not in AWX_UPGRADE_METHODS and upgrade_method not in CR_UPGRADE_METHODS:
                    print(f"  Skipping {label}: upgrade method '{upgrade_method}' is not supported")
                    skipped += 1
                    continue

                if upgrade_method in CR_UPGRADE_METHODS:
                    context = app_data.get("Context", "") or ""
                    namespace = app_data.get("Namespace", "") or ""
                    manifest_rel = f"{app_name}/manifests/{app_name}-{instance}.yaml"
                    extra_manifests = app_data.get("Extra_Manifests") or []

                    if not force:
                        current_version = app_data.get("Current_Version", "") or ""
                        latest_version = app_data.get("Latest_Version", "") or ""
                        print(f"  Updating manifest for {label}...")
                        manifest_ok = update_manifest_version(
                            manifest_rel, current_version, latest_version, dry_run=dry_run
                        )
                        if not manifest_ok:
                            skipped += 1
                            continue

                        for extra_rel in extra_manifests:
                            print(f"  Updating extra manifest {extra_rel}...")
                            update_manifest_version(extra_rel, current_version, latest_version, dry_run=dry_run)

                        print(f"  Committing and pushing manifests for {label}...")
                        push_ok = git_commit_push_manifest(
                            manifest_rel, app_name, latest_version, dry_run=dry_run,
                            extra_rel_paths=extra_manifests,
                        )
                        if not push_ok:
                            skipped += 1
                            continue

                        manifests_updated += 1
                    else:
                        print(f"  Skipping manifest update for {label} (--force)")

                    print(f"  Applying manifest for {label}...")
                    if kubectl_apply_manifest(manifest_rel, context, namespace, instance, dry_run=dry_run):
                        launched += 1
                        self._record_upgrade(idx, upgrade_method, dry_run)
                    else:
                        skipped += 1
                    continue

                if upgrade_method in MANIFEST_UPGRADE_METHODS and not force:
                    current_version = app_data.get("Current_Version", "") or ""
                    latest_version = app_data.get("Latest_Version", "") or ""
                    manifest_rel = f"{app_name}/manifests/{app_name}-{instance}.yaml"

                    print(f"  Updating manifest for {label}...")
                    manifest_ok = update_manifest_version(
                        manifest_rel, current_version, latest_version, dry_run=dry_run
                    )
                    if not manifest_ok:
                        skipped += 1
                        continue

                    print(f"  Committing and pushing manifest for {label}...")
                    push_ok = git_commit_push_manifest(
                        manifest_rel, app_name, latest_version, dry_run=dry_run
                    )
                    if not push_ok:
                        skipped += 1
                        continue

                    manifests_updated += 1
                elif upgrade_method in MANIFEST_UPGRADE_METHODS and force:
                    print(f"  Skipping manifest update for {label} (--force)")

                elif upgrade_method in HELM_UPGRADE_METHODS and not force:
                    current_version = app_data.get("Current_Version", "") or ""
                    latest_version = app_data.get("Latest_Version", "") or ""
                    helm_values_file = app_data.get("Helm_Values_File", "") or ""

                    if not helm_values_file:
                        print(f"  Skipping {label}: helm_values_file not set in note")
                        skipped += 1
                        continue

                    print(f"  Updating helm values for {label}...")
                    values_ok = update_helm_values_version(
                        helm_values_file, current_version, latest_version, dry_run=dry_run
                    )
                    if not values_ok:
                        skipped += 1
                        continue

                    print(f"  Committing and pushing helm values for {label}...")
                    push_ok = git_commit_push_manifest(
                        helm_values_file, app_name, latest_version, dry_run=dry_run
                    )
                    if not push_ok:
                        skipped += 1
                        continue

                    manifests_updated += 1
                elif upgrade_method in HELM_UPGRADE_METHODS and force:
                    print(f"  Skipping helm values update for {label} (--force)")

                if upgrade_method in AWX_UPGRADE_METHODS:
                    if app_name == "vault":
                        print(f"  Deferring shared AWX vault upgrade workflow for {label}...")
                        vault_pending.append(idx)
                        continue
                    print(f"  Triggering AWX upgrade for {label} (method: {upgrade_method})...")
                    if trigger_awx_upgrade(f"{app_name}-{instance}", instance, dry_run=dry_run):
                        launched += 1
                        self._record_upgrade(idx, upgrade_method, dry_run)
                    else:
                        skipped += 1
                continue

            print(f"  Skipping {label}: version_pin '{version_pin}' not handled by --upgrade")
            skipped += 1

        if vault_pending:
            first_instance = self.get_row_data(vault_pending[0]).get("Instance", "prod")
            print(f"  Triggering AWX vault upgrade workflow (covers {len(vault_pending)} instance(s))...")
            if trigger_vault_upgrade_workflow(first_instance, dry_run=dry_run):
                launched += 1
                for i, pidx in enumerate(vault_pending):
                    detail = "" if i == 0 else "covered by shared vault upgrade workflow"
                    self._record_upgrade(pidx, "ansible-helm", dry_run, detail=detail)
            else:
                skipped += len(vault_pending)

        print()
        if dry_run:
            print(f"[DRY RUN] Would have updated {manifests_updated} manifest(s), triggered {launched} upgrade(s), skipped {skipped}")
        else:
            print(f"Updated {manifests_updated} manifest(s), triggered {launched} upgrade(s), skipped {skipped}")


if __name__ == "__main__":
    print("Use check_versions.py to interact with the version checker.")
    print("Run: ./check_versions.py --help")
