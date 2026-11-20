#!/usr/bin/env python3
"""PVE operator actions; never print credentials or raw API errors."""
import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error
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
MEDIA_HOSTS = ("stream.rafael.ink", "pictures.rafael.ink")
MEDIA_ROLLBACK = Path("/srv/appdata/docker/cloudflare-blog-tunnel/media-trial-20261120/dns-before.json")


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
        # pct/Compose inherit exported values, which take precedence over --env-file.
        os.environ[key] = value
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
    # Keep the current bytes and the registry reference used by WUD.
    image = run("pct", "exec", "110", "--", "docker", "inspect", "cloudflare-ddns",
                "--format", "{{.Image}}", capture_output=True).stdout.strip()
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
        raise ValueError("Cannot establish DDNS rollback image")
    tagged = run("pct", "exec", "110", "--", "docker", "image", "inspect",
                 "favonia/cloudflare-ddns:latest", "--format", "{{.Id}}", capture_output=True).stdout.strip()
    if tagged != image:
        raise ValueError("Local DDNS tag differs from the running image; reconcile before changing domains")
    with tempfile.TemporaryDirectory(prefix="blog-tunnel-", dir="/run") as directory:
        guest_env = directory + "/env"
        run("pct", "exec", "110", "--", "mkdir", "-m", "0700", directory)
        try:
            run("pct", "push", "110", str(ENV), guest_env, "--perms", "0600")
            compose = ["pct", "exec", "110", "--", "docker", "compose", "--env-file", guest_env,
                       "-f", "/opt/dothomelab/hosts/infra/services/compose.yaml"]
            run(*compose, "config", "--quiet")
            run(*compose, "up", "-d", "--no-deps", "--pull", "never", "cloudflare-ddns")
            if running_domains() != dict(parse(ENV))["DOMAINS"]:
                raise RuntimeError("Running DDNS domains do not match the saved environment")
        finally:
            run("pct", "exec", "110", "--", "rm", "-f", guest_env)
            run("pct", "exec", "110", "--", "rmdir", directory)


def running_domains():
    result = run("pct", "exec", "110", "--", "docker", "inspect", "cloudflare-ddns", capture_output=True)
    values = dict(entry.split("=", 1) for entry in json.loads(result.stdout)[0]["Config"]["Env"])
    return values["DOMAINS"]


def media_trial(action):
    """Save DNS rollback and manage DDNS only; change Cloudflare routes/DNS in Chrome."""
    zones = api("zones?name=" + HOSTNAME)
    if len(zones) != 1:
        raise ValueError("Expected one Cloudflare zone")
    zone = zones[0]["id"]
    records = []
    for hostname in MEDIA_HOSTS:
        matches = [r for r in api(f"zones/{zone}/dns_records?name={hostname}")
                   if r["type"] in ("A", "AAAA", "CNAME")]
        if len(matches) != 1:
            raise ValueError("Expected one address record per media hostname")
        records.append({"record_id": matches[0]["id"], "record": record_body(matches[0])})
    current = dict(parse(ENV))["DOMAINS"]
    if action == "snapshot-media-trial":
        if any(item["record"]["type"] != "A" for item in records):
            raise ValueError("Expected pre-trial media A records")
        data = {"zone": zone, "records": records, "domains_before": current,
                "tunnel_id": DECLARED["tunnel_id"]}
        MEDIA_ROLLBACK.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if MEDIA_ROLLBACK.exists():
            if json.loads(MEDIA_ROLLBACK.read_text()) != data:
                raise ValueError("Retained media rollback differs; inspect before proceeding")
        else:
            fd = os.open(MEDIA_ROLLBACK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(json.dumps(data, indent=2) + "\n")
        if json.loads(MEDIA_ROLLBACK.read_text()) != data:
            raise RuntimeError("Media rollback read-back failed")
        print("Verified focused media DNS/DDNS rollback:", MEDIA_ROLLBACK)
        return
    before = json.loads(MEDIA_ROLLBACK.read_text())
    if before["zone"] != zone or before["tunnel_id"] != DECLARED["tunnel_id"]:
        raise ValueError("Media rollback belongs to a different zone or tunnel")
    # Restore DNS in the dashboard first; do not let DDNS replace live CNAMEs.
    # The dashboard replaces record IDs when changing A <-> CNAME.
    if action == "restore-media-ddns":
        matches = ([item["record"] for item in before["records"]] ==
                   [item["record"] for item in records])
    else:
        matches = before["records"] == records
    if not matches:
        raise ValueError("Media DNS differs from rollback; inspect or restore DNS in Chrome first")
    names = [name.strip() for name in before["domains_before"].split(",") if name.strip()]
    if any("*" in name for name in names) or not set(MEDIA_HOSTS).issubset(names):
        raise ValueError("Unexpected original media DDNS ownership")
    remaining = ",".join(name for name in names if name not in MEDIA_HOSTS)
    if not remaining:
        raise ValueError("Refusing an empty DDNS domain list")
    if current not in (before["domains_before"], remaining):
        raise ValueError("DDNS changed since media snapshot; refusing to overwrite")
    if running_domains() not in (before["domains_before"], remaining):
        raise ValueError("Running DDNS differs from media snapshot")
    desired = before["domains_before"] if action == "restore-media-ddns" else remaining
    save_env("DOMAINS", desired)
    restart_ddns()
    print("Verified media DDNS restoration" if action == "restore-media-ddns"
          else "Verified DDNS excludes only the two media trial hostnames")


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
    allowed_domains = (expected_domains, previous["domains"]) if rollback else (expected_domains,)
    if dict(parse(ENV))["DOMAINS"] not in allowed_domains:
        raise ValueError("DDNS must exclude the apex before changing DNS")
    if not rollback:
        if running_domains() != expected_domains:
            raise ValueError("Running DDNS must exclude the apex before changing DNS")
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
    parser.add_argument("action", choices=["store-token", "prepare-dns", "switch-dns", "rollback-dns", "check",
                                          "snapshot-media-trial", "prepare-media-trial", "restore-media-ddns"])
    args = parser.parse_args()
    if args.action in ("snapshot-media-trial", "prepare-media-trial", "restore-media-ddns"):
        media_trial(args.action)
    elif args.action == "store-token":
        supplied = getpass.getpass("Paste Cloudflare token or install command (hidden): ").strip()
        match = re.search(r"(?:^|\s)(eyJ[A-Za-z0-9+/=]+)(?:\s|$)", supplied)
        token = match.group(1) if match else supplied
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
