#!/usr/bin/env python3
"""PVE operator actions; never print credentials or raw API errors."""
import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "common"))
from dotenv import parse

DECLARED = json.loads((HERE / "ingress.json").read_text())
HOSTNAME = "rafael.ink"
TARGET = DECLARED["tunnel_id"] + ".cfargotunnel.com"
ENV = Path("/root/.env")
ROLLBACK = Path("/srv/appdata/docker/cloudflare-blog-tunnel/ingress-before-tunnel-20261104")
TOKEN_KEY = "CLOUDFLARE_BLOG_TUNNEL_TOKEN"


def validate_token(token):
    try:
        data = json.loads(base64.b64decode(token, validate=True))
        valid = (data["t"] == DECLARED["tunnel_id"]
                 and data["a"] == DECLARED["account_id"] and bool(data["s"]))
    except (ValueError, KeyError, TypeError):
        valid = False
    if not valid:
        raise ValueError("Credential is not for the declared blog tunnel")


def replace_value(text, key, value):
    if not re.fullmatch(r"[A-Za-z0-9_.,:/+=@-]+", value):
        raise ValueError("Unsafe dotenv value; no change made")
    pattern = re.compile(r"^(?:export\s+)?" + re.escape(key) + r"\s*=.*$", re.M)
    if len(pattern.findall(text)) > 1:
        raise ValueError("Duplicate dotenv key; reconcile before continuing")
    line = key + "=" + value
    return pattern.sub(line, text) if pattern.search(text) else text.rstrip("\n") + "\n" + line + "\n"


def without_apex(domains):
    names = [name.strip() for name in domains.split(",") if name.strip()]
    if any("*" in name for name in names):
        raise ValueError("Wildcard DDNS needs separate review")
    remaining = [name for name in names if name != HOSTNAME]
    if not remaining:
        raise ValueError("Refusing an empty DDNS domain list")
    return ",".join(remaining)


def save_env(key, value):
    updated = replace_value(ENV.read_text(), key, value)
    fd, temporary = tempfile.mkstemp(prefix=".env.blog-tunnel-", dir=ENV.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        parse(Path(temporary))
        os.replace(temporary, ENV)
    finally:
        Path(temporary).unlink(missing_ok=True)


def backup_env():
    ROLLBACK.mkdir(parents=True, mode=0o700, exist_ok=True)
    destination = ROLLBACK / "root.env.before"
    if not destination.exists():
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(ENV.read_bytes())
    return destination


def api(path, method="GET", body=None):
    request = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/" + path,
        data=None if body is None else json.dumps(body).encode(), method=method,
        headers={"Authorization": "Bearer " + os.environ["CLOUDFLARE_API_TOKEN"],
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Cloudflare API HTTP {error.code}; credentials and response suppressed") from None
    if not result.get("success"):
        raise RuntimeError("Cloudflare API rejected the request; response suppressed")
    return result["result"]


def apex_record():
    zones = api("zones?name=" + HOSTNAME)
    if len(zones) != 1:
        raise ValueError("Expected one Cloudflare zone")
    zone = zones[0]["id"]
    records = api(f"zones/{zone}/dns_records?name={HOSTNAME}")
    records = [record for record in records if record["type"] in ("A", "AAAA", "CNAME")]
    if len(records) != 1:
        raise ValueError("Expected exactly one apex address record; inspect before changing")
    return zone, records[0]


def record_body(record):
    return {key: record[key] for key in ("type", "name", "content", "ttl", "proxied", "comment", "tags") if key in record}


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def restart_ddns():
    # Pin the currently running image while changing only its domain setting.
    image = run("pct", "exec", "110", "--", "docker", "inspect", "cloudflare-ddns",
                "--format", "{{.Image}}", capture_output=True).stdout.strip()
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
        raise ValueError("Cannot establish DDNS rollback image")
    with tempfile.TemporaryDirectory(prefix="blog-tunnel-", dir="/run") as directory:
        override = Path(directory) / "override.json"
        override.write_text(json.dumps({"services": {"cloudflare-ddns": {"image": image}}}))
        guest_env = directory + "/env"
        guest_override = directory + "/override.json"
        run("pct", "exec", "110", "--", "mkdir", "-m", "0700", directory)
        try:
            run("pct", "push", "110", str(ENV), guest_env, "--perms", "0600")
            run("pct", "push", "110", str(override), guest_override, "--perms", "0600")
            compose = ["pct", "exec", "110", "--", "docker", "compose", "--env-file", guest_env,
                       "-f", "/opt/dothomelab/hosts/infra/services/compose.yaml", "-f", guest_override]
            run(*compose, "config", "--quiet")
            run(*compose, "up", "-d", "--no-deps", "--pull", "never", "cloudflare-ddns")
        finally:
            run("pct", "exec", "110", "--", "rm", "-f", guest_env, guest_override)
            run("pct", "exec", "110", "--", "rmdir", directory)


def prepare():
    backup_env()
    snapshot = ROLLBACK / "dns.json"
    if not snapshot.exists():
        zone, record = apex_record()
        if record["type"] != "A":
            raise ValueError("Expected the pre-cutover apex A record")
        snapshot.write_text(json.dumps({"zone": zone, "record": record_body(record),
                                        "record_id": record["id"], "domains": os.environ["DOMAINS"]}, indent=2) + "\n")
        snapshot.chmod(0o600)
    previous = json.loads(snapshot.read_text())
    expected = without_apex(previous["domains"])
    current = dict(parse(ENV))["DOMAINS"]
    if current not in (previous["domains"], expected):
        raise ValueError("DDNS domains changed since snapshot; inspect first")
    save_env("DOMAINS", expected)
    restart_ddns()
    print("DDNS now excludes only rafael.ink; original DNS and environment retained at", ROLLBACK)


def switch_dns(rollback=False):
    previous = json.loads((ROLLBACK / "dns.json").read_text())
    zone, record = apex_record()
    if zone != previous["zone"] or record["id"] != previous["record_id"]:
        raise ValueError("DNS identity changed; inspect before continuing")
    desired = {**previous["record"], "type": "CNAME", "content": TARGET, "ttl": 1, "proxied": True}
    if record_body(record) not in (previous["record"], desired):
        raise ValueError("DNS changed since snapshot; refusing to overwrite")
    expected_domains = without_apex(previous["domains"])
    if dict(parse(ENV))["DOMAINS"] != expected_domains:
        raise ValueError("DDNS must exclude the apex before changing DNS")
    if not rollback:
        run("pct", "exec", "110", "--", "docker", "exec", "cloudflare-blog-tunnel",
            "cloudflared", "tunnel", "--metrics", "127.0.0.1:2000", "ready")
    api(f"zones/{zone}/dns_records/{record['id']}", "PUT", previous["record"] if rollback else desired)
    _, actual = apex_record()
    if record_body(actual) != (previous["record"] if rollback else desired):
        raise RuntimeError("DNS read-back did not match requested record")
    if rollback:
        save_env("DOMAINS", previous["domains"])
        restart_ddns()
    print("Original A record restored; CGNAT still prevents inbound access" if rollback else "Verified proxied apex CNAME to the declared tunnel")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["store-token", "prepare-dns", "switch-dns", "rollback-dns", "check"])
    args = parser.parse_args()
    if args.action == "store-token":
        token = getpass.getpass("Blog tunnel token (hidden): ").strip()
        validate_token(token)
        existing = dict(parse(ENV)).get(TOKEN_KEY)
        if existing and existing != token:
            raise ValueError("Existing token differs; rotation requires separate review")
        backup_env()
        save_env(TOKEN_KEY, token)
        print("Declared connector credential saved to /root/.env (0600)")
    elif args.action == "prepare-dns":
        prepare()
    elif args.action == "switch-dns":
        switch_dns()
    elif args.action == "rollback-dns":
        switch_dns(rollback=True)
    else:
        validate_token(os.environ[TOKEN_KEY])
        print("Declared connector credential is present; value suppressed")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"Blog tunnel operation failed: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
