#!/usr/bin/env python3
"""Provision only Meta Egg's restricted Jellyfin user from an explicit admin token file."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import secrets
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hosts/common'))
from dotenv import parse

PREFIX = 'STAGING_META_EGG_JELLYFIN_'
NAME = 'meta-egg-staging'
AUTH = 'MediaBrowser Client="Meta Egg staging", Device="Meta Egg staging", DeviceId="dothomelab-meta-egg-staging", Version="1"'
DENIED = ('IsAdministrator', 'EnableCollectionManagement', 'EnableSubtitleManagement',
          'EnableLyricManagement', 'EnableUserPreferenceAccess', 'EnableRemoteControlOfOtherUsers',
          'EnableSharedDeviceControl', 'EnableRemoteAccess', 'EnableLiveTvManagement',
          'EnableLiveTvAccess', 'EnableAudioPlaybackTranscoding', 'EnableVideoPlaybackTranscoding',
          'EnablePlaybackRemuxing', 'ForceRemoteSourceTranscoding', 'EnableContentDeletion',
          'EnableContentDownloading', 'EnableSyncTranscoding', 'EnableMediaConversion',
          'EnableAllChannels', 'EnableAllFolders', 'EnablePublicSharing')


class SetupError(RuntimeError):
    """Only sanitized, locally authored messages may be displayed."""


class ApiError(SetupError):
    def __init__(self, status):
        self.status = status
        super().__init__(f'Jellyfin request returned HTTP {status}; response withheld')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url, token, method, endpoint, payload=None):
    headers = {'Accept': 'application/json', 'Authorization': AUTH}
    if token:
        headers['X-Emby-Token'] = token
    body = None
    if payload is not None:
        body = json.dumps(payload).encode()
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url + endpoint, data=body, headers=headers, method=method)
    # Credentials never follow redirects or environment-configured HTTP proxies.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(req, timeout=30) as response:
            body = response.read()
        return json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        raise ApiError(error.code) from None
    except (OSError, ValueError):
        raise SetupError('Jellyfin request failed or returned invalid JSON; details withheld') from None


def private_file(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise SetupError('Credential and environment inputs must be regular files private to their owner')


def write_env(path, values):
    if set(values) - {'URL', 'PASSWORD', 'USER_ID', 'API_KEY'}:
        raise SetupError('Refusing an unowned environment key')
    if any(not isinstance(value, str) or '\n' in value or '\r' in value for value in values.values()):
        raise SetupError('Invalid scoped environment value')
    private_file(path)
    keys = {PREFIX + key for key in values}
    lines = path.read_text().splitlines(keepends=True)
    kept = []
    for line in lines:
        match = re.match(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=', line)
        if not match or match.group(1) not in keys:
            kept.append(line)
    content = ''.join(kept)
    if content and not content.endswith('\n'):
        content += '\n'
    for key, value in values.items():
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        content += f'{PREFIX}{key}="{escaped}"\n'
    original = path.stat()
    descriptor, temporary = tempfile.mkstemp(prefix='.meta-egg-env-', dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        os.fchown(descriptor, original.st_uid, original.st_gid)
        with os.fdopen(descriptor, 'w') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def restricted_policy(current, folders):
    if not folders:
        raise SetupError('No movie libraries found; refusing unrestricted library access')
    policy = {key: False if isinstance(value, bool) else value for key, value in current.items()}
    policy.update(dict.fromkeys(DENIED, False))
    policy.update(IsHidden=True, IsDisabled=False, EnableMediaPlayback=True,
                  EnableAllDevices=True, EnabledDevices=[], EnabledChannels=[],
                  EnabledFolders=sorted(folders), EnableContentDeletionFromFolders=[],
                  SyncPlayAccess='None')
    return policy


def user_id(user):
    try:
        if user['Name'] != NAME:
            raise ValueError()
        return UUID(user['Id']).hex
    except (KeyError, TypeError, ValueError):
        raise SetupError('Jellyfin returned an unexpected integration user identity') from None


def owned_token(url, user, state):
    identity = user_id(user)
    if state.get('USER_ID') and UUID(state['USER_ID']).hex != identity:
        raise SetupError('Existing same-name user differs from the saved integration identity')
    if not state.get('PASSWORD'):
        raise SetupError('Same-name user has no saved integration password; refusing adoption')
    token = state.get('API_KEY')
    if token and state.get('USER_ID'):
        try:
            if user_id(request(url, token, 'GET', '/Users/Me')) != identity:
                raise SetupError('Saved integration token belongs to another user')
            return token
        except ApiError as error:
            if error.status not in (400, 401, 403):
                raise
    result = request(url, '', 'POST', '/Users/AuthenticateByName',
                     {'Username': NAME, 'Pw': state['PASSWORD']})
    if user_id(result['User']) != identity or not result.get('AccessToken'):
        raise SetupError('Retained integration credentials do not prove account ownership')
    return result['AccessToken']


def provision(url, admin_token, env_file):
    values = dict(parse(env_file))
    state = {key.removeprefix(PREFIX): value for key, value in values.items() if key.startswith(PREFIX)}
    if any(state.get(key) for key in ('PASSWORD', 'USER_ID', 'API_KEY')) and state.get('URL') != url:
        raise SetupError('Saved integration credentials belong to a different server URL')
    folders = sorted({str(UUID(folder['ItemId'])) for folder in request(url, admin_token, 'GET', '/Library/VirtualFolders')
                      if folder.get('CollectionType') == 'movies'})
    if not folders:
        raise SetupError('No movie libraries found; no account was changed')
    users = [user for user in request(url, admin_token, 'GET', '/Users') if user['Name'].casefold() == NAME]
    if len(users) > 1:
        raise SetupError('Ambiguous integration user name; no account was changed')
    if users:
        user = users[0]
        token = owned_token(url, user, state)
    else:
        if state.get('USER_ID') or state.get('API_KEY'):
            raise SetupError('Saved integration user is missing; refusing automatic recreation')
        state['PASSWORD'] = state.get('PASSWORD') or secrets.token_urlsafe(48)
        # Save before creation: a retry can prove ownership if the response is lost.
        write_env(env_file, {'URL': url, 'PASSWORD': state['PASSWORD']})
        user = request(url, admin_token, 'POST', '/Users/New', {'Name': NAME, 'Password': state['PASSWORD']})
        state['USER_ID'] = user_id(user)
        write_env(env_file, {'USER_ID': state['USER_ID']})
        token = None
    identity = user_id(user)
    policy = restricted_policy(user['Policy'], folders)
    if user['Policy'] != policy:
        request(url, admin_token, 'POST', f'/Users/{identity}/Policy', policy)
    checked = request(url, admin_token, 'GET', f'/Users/{identity}')
    if user_id(checked) != identity or any(checked['Policy'].get(key) != value for key, value in policy.items()):
        raise SetupError('Restricted integration policy did not verify; credentials withheld from staging')
    token = token or owned_token(url, user, state)
    write_env(env_file, {'URL': url, 'USER_ID': identity, 'API_KEY': token})
    print(f'Meta Egg Jellyfin account verified: hidden non-admin, {len(folders)} movie libraries; secrets withheld')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admin-token-file', type=Path, required=True)
    parser.add_argument('--url', default='http://192.168.0.112:8096')
    parser.add_argument('--env-file', type=Path, default=Path('/root/.env'))
    args = parser.parse_args()
    os.umask(0o077)
    try:
        url = args.url.rstrip('/')
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or
                parsed.password or parsed.query or parsed.fragment or any(char.isspace() for char in url)):
            raise SetupError('Use a credential-free HTTP(S) Jellyfin base URL without query or fragment')
        private_file(args.admin_token_file)
        private_file(args.env_file)
        token = args.admin_token_file.read_text().strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]+', token):
            raise SetupError('Invalid administrator token file')
        with args.env_file.with_name(args.env_file.name + '.meta-egg.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            provision(url, token, args.env_file)
        return 0
    except SetupError as error:
        print(str(error), file=sys.stderr)
    except Exception:
        print('Integration setup failed; retained credentials allow a reviewed retry. Details withheld.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
