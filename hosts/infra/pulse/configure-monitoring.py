#!/usr/bin/env python3
"""Reconcile Pulse's PVE source and Docker agents without logging secrets."""

from __future__ import annotations

import argparse
import http.cookiejar
import importlib.util
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_PATH = Path("/root/.env")
INVENTORY_PATH = REPO_ROOT / "provision/inventory.env"
PULSE_URL = "http://192.168.0.110:7655"
PVE_URL = "https://192.168.0.250:8006"
PVE_USER = "pulse-monitor@pve"
PVE_TOKEN = "dothomelab"
PVE_TOKEN_ID = f"{PVE_USER}!{PVE_TOKEN}"
REQUIRED_APP_CONTAINERS = {
    "infra": {"syncthing"},
}


def run(*args: str, input_text: str | None = None) -> str:
    result = subprocess.run(
        args,
        input=input_text,
        text=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def load_env() -> dict[str, str]:
    spec = importlib.util.spec_from_file_location(
        "dothomelab_dotenv", REPO_ROOT / "hosts/common/dotenv.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the repository dotenv parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(module.parse(ENV_PATH))


def inventory() -> tuple[list[int], dict[int, str]]:
    text = INVENTORY_PATH.read_text(encoding="utf-8")
    match = re.search(r"^PULSE_DOCKER_CTIDS=\(([^)]*)\)$", text, re.MULTILINE)
    if not match:
        raise RuntimeError("PULSE_DOCKER_CTIDS is missing from inventory.env")
    ctids = [int(value) for value in match.group(1).split()]
    names = {
        int(ctid): name
        for ctid, name in re.findall(
            r'^CT_HOSTNAME\[([0-9]+)\]="([^"]+)"$', text, re.MULTILINE
        )
    }
    if not ctids or any(ctid not in names for ctid in ctids):
        raise RuntimeError("Pulse Docker CTIDs do not map to declared hostnames")
    return ctids, names


def set_env_value(key: str, value: str) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    encoded = value.replace("\\", "\\\\").replace('"', '\\"')
    replacement = f'{key}="{encoded}"'
    pattern = re.compile(rf"^(?:export\s+)?{re.escape(key)}\s*=")
    output: list[str] = []
    replaced = False
    for line in lines:
        if pattern.match(line):
            if not replaced:
                output.append(replacement)
                replaced = True
        else:
            output.append(line)
    if not replaced:
        output.extend(["", replacement])
    temporary = ENV_PATH.with_name(f".{ENV_PATH.name}.pulse.tmp")
    temporary.write_text("\n".join(output) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, ENV_PATH)


def ensure_pve_token(env: dict[str, str]) -> str:
    users = json.loads(run("pveum", "user", "list", "--output-format", "json"))
    if not any(row.get("userid") == PVE_USER for row in users):
        run("pveum", "user", "add", PVE_USER, "--comment", "Pulse read-only monitor")
    run(
        "pveum",
        "acl",
        "modify",
        "/",
        "--users",
        PVE_USER,
        "--roles",
        "PVEAuditor",
        "--propagate",
        "1",
    )

    tokens = json.loads(
        run("pveum", "user", "token", "list", PVE_USER, "--output-format", "json")
    )
    exists = any(row.get("tokenid") == PVE_TOKEN for row in tokens)
    secret = env.get("PULSE_PVE_TOKEN_SECRET", "")
    if exists and not secret:
        raise RuntimeError(
            f"{PVE_TOKEN_ID} exists but PULSE_PVE_TOKEN_SECRET is unavailable; "
            "do not rotate it implicitly"
        )
    if not exists:
        created = json.loads(
            run(
                "pveum",
                "user",
                "token",
                "add",
                PVE_USER,
                PVE_TOKEN,
                "--privsep",
                "0",
                "--comment",
                "Pulse PVEAuditor token",
                "--output-format",
                "json",
            )
        )
        secret = str(created.get("value", ""))
        if not secret:
            raise RuntimeError("Proxmox did not return the new Pulse token secret")
        set_env_value("PULSE_PVE_TOKEN_SECRET", secret)
    return secret


class Pulse:
    def __init__(self, username: str, password: str) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )
        self.request(
            "POST",
            "/api/login",
            {"username": username, "password": password},
            csrf=False,
        )

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        *,
        csrf: bool = True,
    ) -> object:
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            f"{PULSE_URL}{path}",
            data=data,
            method=method,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        if csrf and method not in {"GET", "HEAD"}:
            token = next(
                (cookie.value for cookie in self.jar if cookie.name == "pulse_csrf"),
                "",
            )
            if token:
                request.add_header("X-CSRF-Token", token)
        try:
            with self.opener.open(request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")
            raise RuntimeError(
                f"Pulse {method} {path} returned HTTP {error.code}: {detail[:400]}"
            ) from error
        return json.loads(raw) if raw else {}


def resource_rows(pulse: Pulse, resource_type: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    page = 1
    while True:
        response = pulse.request(
            "GET",
            "/api/resources?"
            f"type={urllib.parse.quote(resource_type, safe='')}&page={page}&limit=100",
        )
        if isinstance(response, list):
            return [row for row in response if isinstance(row, dict)]
        if (
            not isinstance(response, dict)
            or not isinstance(response.get("data"), list)
        ):
            raise RuntimeError(
                f"Pulse returned invalid {resource_type} resource pagination"
            )
        rows.extend(row for row in response["data"] if isinstance(row, dict))
        meta = response.get("meta")
        total_pages = int(meta.get("totalPages", 1)) if isinstance(meta, dict) else 1
        if page >= total_pages:
            return rows
        page += 1


def reconcile_pve(pulse: Pulse, secret: str) -> None:
    nodes = pulse.request("GET", "/api/config/nodes")
    if not isinstance(nodes, list):
        raise RuntimeError("Pulse returned an invalid node list")
    existing = next(
        (
            node
            for node in nodes
            if isinstance(node, dict)
            and node.get("type") == "pve"
            and node.get("name") == "afa"
        ),
        None,
    )
    payload: dict[str, object] = {
        "type": "pve",
        "name": "afa",
        "host": PVE_URL,
        "user": PVE_USER,
        "tokenName": PVE_TOKEN_ID,
        "tokenValue": secret,
        "verifySSL": False,
        "monitorVMs": True,
        "monitorContainers": True,
        "monitorStorage": True,
        "monitorBackups": True,
        "monitorPhysicalDisks": False,
        "temperatureMonitoringEnabled": False,
    }
    if existing:
        node_id = str(existing.get("id", ""))
        if not node_id:
            raise RuntimeError("existing Pulse PVE source has no id")
        pulse.request(
            "PUT",
            f"/api/config/nodes/{urllib.parse.quote(node_id, safe='')}",
            payload,
        )
    else:
        pulse.request("POST", "/api/config/nodes", payload)


def agent_unit(ctid: int) -> tuple[bool, str]:
    try:
        active = run("pct", "exec", str(ctid), "--", "systemctl", "is-active", "pulse-agent")
        unit = run("pct", "exec", str(ctid), "--", "systemctl", "cat", "pulse-agent")
    except subprocess.CalledProcessError:
        return False, ""
    return active.strip() == "active", unit


def agent_ready(ctid: int) -> bool:
    active, unit = agent_unit(ctid)
    return (
        active
        and "--enable-host" in unit
        and "--enable-docker" in unit
        and "--enable-commands" in unit
    )


def agent_id(ctid: int) -> str:
    try:
        value = run(
            "pct",
            "exec",
            str(ctid),
            "--",
            "cat",
            "/var/lib/pulse-agent/agent-id",
        ).strip()
    except subprocess.CalledProcessError:
        return ""
    if value and not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", value):
        raise RuntimeError(f"Pulse agent ID in LXC {ctid} has an invalid shape")
    return value


def command_capable_host(row: object) -> str:
    if not isinstance(row, dict) or row.get("status") != "online":
        return ""
    docker = row.get("docker")
    source_status = row.get("sourceStatus")
    capabilities = row.get("capabilities")
    if (
        not isinstance(docker, dict)
        or not isinstance(source_status, dict)
        or not isinstance(source_status.get("docker"), dict)
        or source_status["docker"].get("status") != "online"
        or not isinstance(capabilities, list)
        or not any(
            isinstance(capability, dict) and capability.get("name") == "restart"
            for capability in capabilities
        )
    ):
        return ""
    return str(docker.get("hostname", "")).lower()


def command_capable_hosts(pulse: Pulse) -> set[str]:
    return {
        hostname
        for row in resource_rows(pulse, "app-container")
        if (hostname := command_capable_host(row))
    }


def download_agent_installer(ctid: int, guest_installer: str) -> None:
    run(
        "pct",
        "exec",
        str(ctid),
        "--",
        "curl",
        "--fail",
        "--silent",
        "--show-error",
        f"{PULSE_URL}/install.sh",
        "--output",
        guest_installer,
    )


def install_agent(pulse: Pulse, ctid: int, hostname: str) -> None:
    response = pulse.request(
        "POST",
        "/api/agent-install-command",
        {"type": "host", "enableCommands": True, "name": f"dothomelab-{hostname}"},
    )
    if not isinstance(response, dict) or not response.get("token"):
        raise RuntimeError(f"Pulse did not mint an install token for LXC {ctid}")
    token = str(response["token"])
    with tempfile.NamedTemporaryFile(
        mode="w", prefix=f"pulse-agent-{ctid}-", dir="/run", delete=False
    ) as handle:
        handle.write(token)
        token_path = Path(handle.name)
    os.chmod(token_path, 0o600)
    guest_token = "/run/dothomelab-pulse-agent.token"
    guest_installer = "/run/dothomelab-pulse-agent-install.sh"
    current_agent_id = agent_id(ctid)
    try:
        run("pct", "push", str(ctid), str(token_path), guest_token, "--perms", "0600")
        download_agent_installer(ctid, guest_installer)
        installer_args = [
            "pct",
            "exec",
            str(ctid),
            "--",
            "bash",
            guest_installer,
            "--url",
            PULSE_URL,
            "--token-file",
            guest_token,
            "--enable-host",
            "--enable-docker",
            "--enable-commands",
        ]
        if current_agent_id:
            installer_args.extend(["--agent-id", current_agent_id])
        installer_args.extend(["--hostname", hostname, "--non-interactive"])
        run(*installer_args)
    finally:
        token_path.unlink(missing_ok=True)
        subprocess.run(
            [
                "pct",
                "exec",
                str(ctid),
                "--",
                "rm",
                "-f",
                guest_token,
                guest_installer,
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def wait_for_resources(pulse: Pulse, ctids: list[int], names: dict[int, str]) -> None:
    deadline = time.monotonic() + 240
    last_summary = ""
    while time.monotonic() < deadline:
        nodes = pulse.request("GET", "/api/config/nodes")
        pve_ok = any(
            isinstance(node, dict)
            and node.get("type") == "pve"
            and node.get("name") == "afa"
            and node.get("status") in {"connected", "online"}
            for node in nodes if isinstance(nodes, list)
        )
        pve_resources = resource_rows(pulse, "system-container")
        agents = resource_rows(pulse, "agent")
        containers = resource_rows(pulse, "app-container")
        observed_vmids = {
            int(row.get("proxmox", {}).get("vmid"))
            for row in pve_resources
            if isinstance(row, dict)
            and isinstance(row.get("proxmox"), dict)
            and row["proxmox"].get("vmid") is not None
        }
        missing_lxcs = [
            str(ctid)
            for ctid in [
                int(line.split()[0])
                for line in run("pct", "list").splitlines()[1:]
                if line.split()
            ]
            if ctid not in observed_vmids
        ]
        observed_docker_hosts = {
            str(row.get("docker", {}).get("hostname", "")).lower()
            for row in agents
            if isinstance(row, dict) and isinstance(row.get("docker"), dict)
        }
        missing_docker_hosts = [
            names[ctid]
            for ctid in ctids
            if names[ctid].lower() not in observed_docker_hosts
        ]
        missing_containers: dict[str, list[str]] = {}
        observed_containers: dict[str, set[str]] = {}
        for ctid in ctids:
            expected = {
                line
                for line in run(
                    "pct",
                    "exec",
                    str(ctid),
                    "--",
                    "docker",
                    "ps",
                    "--format",
                    "{{.Names}}",
                ).splitlines()
                if line
            }
            observed = {
                str(row.get("name", ""))
                for row in containers
                if isinstance(row, dict)
                and isinstance(row.get("docker"), dict)
                and str(row["docker"].get("hostname", "")).lower()
                == names[ctid].lower()
                and row.get("status") == "online"
            }
            observed_containers[names[ctid].lower()] = observed
            missing = sorted(expected - observed)
            if missing:
                missing_containers[names[ctid]] = missing
        missing_required_containers = {
            hostname: sorted(required - observed_containers.get(hostname, set()))
            for hostname, required in REQUIRED_APP_CONTAINERS.items()
            if required - observed_containers.get(hostname, set())
        }
        command_hosts = {
            hostname
            for row in containers
            if (hostname := command_capable_host(row))
        }
        missing_command_hosts = [
            names[ctid]
            for ctid in ctids
            if names[ctid].lower() not in command_hosts
        ]
        last_summary = (
            f"pve_connected={pve_ok} missing_lxcs={missing_lxcs} "
            f"missing_docker_hosts={missing_docker_hosts} "
            f"missing_containers={missing_containers} "
            f"missing_required_containers={missing_required_containers} "
            f"missing_command_hosts={missing_command_hosts}"
        )
        if (
            pve_ok
            and not missing_lxcs
            and not missing_docker_hosts
            and not missing_containers
            and not missing_required_containers
            and not missing_command_hosts
        ):
            return
        time.sleep(10)
    raise RuntimeError(f"Pulse inventory did not converge: {last_summary}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("run on the Proxmox host as root")

    env = load_env()
    required = ("PULSE_AUTH_USER", "PULSE_AUTH_PASS")
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise SystemExit(f"missing required Pulse variables: {', '.join(missing)}")
    ctids, names = inventory()

    secret = env.get("PULSE_PVE_TOKEN_SECRET", "")
    if not args.verify:
        secret = ensure_pve_token(env)
    elif not secret:
        raise SystemExit("PULSE_PVE_TOKEN_SECRET is missing")

    pulse = Pulse(env["PULSE_AUTH_USER"], env["PULSE_AUTH_PASS"])
    if not args.verify:
        reconcile_pve(pulse, secret)
        command_hosts = command_capable_hosts(pulse)
        for ctid in ctids:
            if not agent_ready(ctid) or names[ctid].lower() not in command_hosts:
                install_agent(pulse, ctid, names[ctid])

    inactive = [str(ctid) for ctid in ctids if not agent_ready(ctid)]
    if inactive:
        raise SystemExit(f"Pulse Docker agents are not ready in LXCs: {', '.join(inactive)}")
    wait_for_resources(pulse, ctids, names)
    print(
        "Pulse monitoring verified: PVE inventories all LXCs and command-enabled "
        f"Docker agents report from CTIDs {', '.join(map(str, ctids))}; required app "
        "containers include infra/syncthing"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
