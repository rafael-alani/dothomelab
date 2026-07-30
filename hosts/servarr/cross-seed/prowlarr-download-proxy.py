#!/usr/bin/env python3
"""Proxy Prowlarr Torznab searches and complete NexusPHP download notices."""

from __future__ import annotations

import base64
import ctypes
import ctypes.util
import hmac
import html.parser
import json
import logging
import os
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PROWLARR_URL = os.environ.get("PROWLARR_URL", "http://127.0.0.1:9696").rstrip("/")
PROWLARR_CONFIG = Path(
    os.environ.get("PROWLARR_CONFIG", "/prowlarr/config.xml")
)
PROWLARR_DB = Path(os.environ.get("PROWLARR_DB", "/prowlarr/prowlarr.db"))
LISTEN_HOST = os.environ.get("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "9697"))
PUBLIC_URL = os.environ.get(
    "PUBLIC_URL", f"http://gluetun:{LISTEN_PORT}"
).rstrip("/")
REQUEST_TIMEOUT = 20
MAX_TORRENT_BYTES = 16 * 1024 * 1024
MAX_TORZNAB_BYTES = 32 * 1024 * 1024
ALLOWED_DEFINITIONS = {
    "dothomelab-btschool",
    "dothomelab-railgunpt",
}
PATH_PATTERN = re.compile(r"^/([0-9]+)/(api|download)$")
LOGGER = logging.getLogger("prowlarr-download-proxy")


class ProxyError(RuntimeError):
    """A safe-to-display proxy failure."""


class ResponseTooLarge(ProxyError):
    """The remote response exceeded its explicit bound."""


@dataclass(frozen=True)
class IndexerContext:
    indexer_id: int
    definition: str
    base_url: str
    cookies: dict[str, str]


@dataclass(frozen=True)
class RemoteResponse:
    status: int
    headers: Any
    body: bytes


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Return redirect responses to the caller instead of following them."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


class NoticeFormParser(html.parser.HTMLParser):
    """Extract the one download-confirmation form without logging its data."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: list[dict[str, Any]] = []
        self.current: dict[str, Any] | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {name.lower(): value or "" for name, value in attrs}
        if tag.lower() == "form":
            self.current = {
                "action": attributes.get("action", ""),
                "method": attributes.get("method", "get").lower(),
                "inputs": {},
                "continuedownload": False,
            }
            return
        if tag.lower() != "input" or self.current is None:
            return
        name = attributes.get("name")
        if not name or "disabled" in attributes:
            return
        input_type = attributes.get("type", "text").lower()
        if input_type in {"checkbox", "radio"} and "checked" not in attributes:
            return
        self.current["inputs"][name] = attributes.get("value", "")
        if attributes.get("id") == "continuedownload":
            self.current["continuedownload"] = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "form" and self.current is not None:
            self.forms.append(self.current)
            self.current = None

    def download_form(self, expected_id: str) -> dict[str, str]:
        matches = [
            form
            for form in self.forms
            if form["continuedownload"]
            and form["method"] == "post"
            and form["action"] == "?"
            and form["inputs"].get("id") == expected_id
            and form["inputs"].get("type") == "firsttime"
            and form["inputs"].get("hidenotice") == "1"
            and form["inputs"].get("submit")
        ]
        if len(matches) != 1:
            raise ProxyError("tracker returned an unexpected download notice")
        return dict(matches[0]["inputs"])


def api_key() -> str:
    try:
        key = ElementTree.parse(PROWLARR_CONFIG).getroot().findtext("ApiKey", "")
    except (ElementTree.ParseError, OSError) as error:
        raise ProxyError("Prowlarr configuration is unavailable") from error
    if not key:
        raise ProxyError("Prowlarr API key is missing")
    return key


def validate_api_key(query: dict[str, list[str]]) -> None:
    supplied = query.get("apikey", [])
    if len(supplied) != 1 or not hmac.compare_digest(supplied[0], api_key()):
        raise PermissionError("invalid Prowlarr API key")


def database_row(statement: str, parameters: tuple[Any, ...]) -> Any:
    last_error: OSError | sqlite3.Error | None = None
    for attempt in range(3):
        connection = None
        try:
            connection = sqlite3.connect(
                f"file:{PROWLARR_DB}?mode=ro", uri=True, timeout=10
            )
            return connection.execute(statement, parameters).fetchone()
        except (OSError, sqlite3.Error) as error:
            last_error = error
            if attempt < 2:
                time.sleep(0.25 * (attempt + 1))
        finally:
            if connection is not None:
                connection.close()
    else:
        raise ProxyError("Prowlarr indexer state is unavailable") from last_error


def indexer_context(indexer_id: int) -> IndexerContext:
    row = database_row(
        """
        SELECT Indexers.Settings, IndexerStatus.Cookies
        FROM Indexers
        LEFT JOIN IndexerStatus
          ON IndexerStatus.ProviderId = Indexers.Id
        WHERE Indexers.Id = ?
        """,
        (indexer_id,),
    )
    if not row:
        raise ProxyError("Prowlarr indexer is missing")
    try:
        settings = json.loads(row[0])
        cookies = json.loads(row[1]) if row[1] else {}
    except (TypeError, json.JSONDecodeError) as error:
        raise ProxyError("Prowlarr indexer state is invalid") from error
    definition = str(settings.get("definitionFile", ""))
    base_url = str(settings.get("baseUrl", ""))
    if definition not in ALLOWED_DEFINITIONS:
        raise ProxyError("Prowlarr indexer is not proxy-enabled")
    parsed_base = urllib.parse.urlsplit(base_url)
    if parsed_base.scheme != "https" or not parsed_base.hostname:
        raise ProxyError("Prowlarr indexer base URL is unsafe")
    if not isinstance(cookies, dict) or not cookies:
        raise ProxyError("Prowlarr tracker session is missing")
    return IndexerContext(
        indexer_id=indexer_id,
        definition=definition,
        base_url=base_url,
        cookies={str(name): str(value) for name, value in cookies.items()},
    )


def read_bounded(response: Any, maximum: int) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            declared_length = int(content_length)
        except ValueError as error:
            raise ProxyError("remote response has an invalid length") from error
        if declared_length < 0 or declared_length > maximum:
            raise ResponseTooLarge("remote response is too large")
    body = response.read(maximum + 1)
    if len(body) > maximum:
        raise ResponseTooLarge("remote response is too large")
    return body


def remote_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    follow_redirects: bool = True,
    maximum: int,
) -> RemoteResponse:
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=headers or {},
    )
    opener = (
        urllib.request.build_opener()
        if follow_redirects
        else urllib.request.build_opener(NoRedirect())
    )
    try:
        with opener.open(request, timeout=REQUEST_TIMEOUT) as response:
            return RemoteResponse(
                status=response.status,
                headers=response.headers,
                body=read_bounded(response, maximum),
            )
    except urllib.error.HTTPError as error:
        if not follow_redirects and 300 <= error.code < 400:
            return RemoteResponse(
                status=error.code,
                headers=error.headers,
                body=read_bounded(error, maximum),
            )
        raise ProxyError(f"remote request returned HTTP {error.code}") from error
    except (OSError, urllib.error.URLError) as error:
        raise ProxyError("remote request failed") from error


def validate_bencoded_torrent(body: bytes) -> None:
    if not body or len(body) > MAX_TORRENT_BYTES:
        raise ProxyError("tracker did not return a bounded torrent")

    def parse(position: int, depth: int) -> tuple[int, set[bytes] | None]:
        if depth > 100 or position >= len(body):
            raise ProxyError("tracker returned invalid bencode")
        token = body[position : position + 1]
        if token == b"i":
            end = body.find(b"e", position + 1)
            if end < 0:
                raise ProxyError("tracker returned invalid bencode")
            integer = body[position + 1 : end]
            if not re.fullmatch(rb"-?(0|[1-9][0-9]*)", integer):
                raise ProxyError("tracker returned invalid bencode")
            return end + 1, None
        if token in {b"l", b"d"}:
            is_dictionary = token == b"d"
            position += 1
            keys: set[bytes] = set()
            previous_key: bytes | None = None
            while position < len(body) and body[position : position + 1] != b"e":
                if is_dictionary:
                    position, key = parse_bytes(position)
                    if previous_key is not None and key <= previous_key:
                        raise ProxyError("tracker returned unsorted bencode")
                    previous_key = key
                    keys.add(key)
                position, _ = parse(position, depth + 1)
            if position >= len(body):
                raise ProxyError("tracker returned invalid bencode")
            return position + 1, keys if is_dictionary else None
        return parse_bytes(position)[0], None

    def parse_bytes(position: int) -> tuple[int, bytes]:
        colon = body.find(b":", position, min(len(body), position + 32))
        if colon < 0:
            raise ProxyError("tracker returned invalid bencode")
        length_text = body[position:colon]
        if not re.fullmatch(rb"0|[1-9][0-9]*", length_text):
            raise ProxyError("tracker returned invalid bencode")
        length = int(length_text)
        start = colon + 1
        end = start + length
        if end > len(body):
            raise ProxyError("tracker returned invalid bencode")
        return end, body[start:end]

    end, top_keys = parse(0, 0)
    if end != len(body) or top_keys is None or b"info" not in top_keys:
        raise ProxyError("tracker returned an invalid torrent dictionary")
    if not ({b"announce", b"announce-list"} & top_keys):
        raise ProxyError("tracker torrent has no announce URL")


def cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{name}={value}" for name, value in sorted(cookies.items()))


def tracker_torrent(context: IndexerContext, tracker_url: str) -> bytes:
    parsed = urllib.parse.urlsplit(tracker_url)
    base = urllib.parse.urlsplit(context.base_url)
    expected_path = urllib.parse.urlsplit(
        urllib.parse.urljoin(context.base_url.rstrip("/") + "/", "download.php")
    ).path
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    torrent_ids = query.get("id", [])
    if (
        parsed.scheme != "https"
        or parsed.hostname != base.hostname
        or parsed.port != base.port
        or parsed.path != expected_path
        or len(torrent_ids) != 1
        or not torrent_ids[0].isdigit()
    ):
        query_keys = ",".join(
            sorted(urllib.parse.parse_qs(parsed.query, keep_blank_values=True))
        )
        raise ProxyError(
            "tracker download URL is outside the allowlist "
            f"(scheme={parsed.scheme or 'none'} "
            f"host_match={parsed.hostname == base.hostname} "
            f"port_match={parsed.port == base.port} "
            f"path={parsed.path or '/'} query_keys={query_keys or 'none'})"
        )

    headers = {
        "Accept": "application/x-bittorrent,text/html;q=0.9,*/*;q=0.1",
        "Cookie": cookie_header(context.cookies),
        "User-Agent": "dothomelab-cross-seed-proxy/1.0",
    }
    first = remote_request(
        tracker_url,
        headers=headers,
        maximum=MAX_TORRENT_BYTES,
    )
    try:
        validate_bencoded_torrent(first.body)
        return first.body
    except ProxyError:
        pass

    content_type = first.headers.get("Content-Type", "").lower()
    if first.status != HTTPStatus.OK or "text/html" not in content_type:
        raise ProxyError("tracker returned neither a torrent nor a notice")
    parser = NoticeFormParser()
    parser.feed(first.body.decode("utf-8", errors="replace"))
    form = parser.download_form(torrent_ids[0])
    payload = urllib.parse.urlencode(form).encode("utf-8")
    post_headers = {
        **headers,
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": tracker_url,
    }
    confirmed = remote_request(
        tracker_url,
        method="POST",
        headers=post_headers,
        data=payload,
        follow_redirects=False,
        maximum=MAX_TORRENT_BYTES,
    )
    validate_bencoded_torrent(confirmed.body)
    return confirmed.body


def aes_256_cbc_decrypt(key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
    library_name = ctypes.util.find_library("crypto")
    if not library_name and Path("/usr/lib/libcrypto.so.3").is_file():
        library_name = "/usr/lib/libcrypto.so.3"
    if not library_name:
        raise ProxyError("libcrypto is unavailable")
    crypto = ctypes.CDLL(library_name)
    crypto.EVP_CIPHER_CTX_new.restype = ctypes.c_void_p
    crypto.EVP_CIPHER_CTX_free.argtypes = [ctypes.c_void_p]
    crypto.EVP_aes_256_cbc.restype = ctypes.c_void_p
    crypto.EVP_DecryptInit_ex.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    crypto.EVP_DecryptInit_ex.restype = ctypes.c_int
    crypto.EVP_DecryptUpdate.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    crypto.EVP_DecryptUpdate.restype = ctypes.c_int
    crypto.EVP_DecryptFinal_ex.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    crypto.EVP_DecryptFinal_ex.restype = ctypes.c_int

    context = crypto.EVP_CIPHER_CTX_new()
    if not context:
        raise ProxyError("AES context allocation failed")
    key_buffer = ctypes.create_string_buffer(key)
    iv_buffer = ctypes.create_string_buffer(iv)
    input_buffer = ctypes.create_string_buffer(ciphertext)
    output_buffer = ctypes.create_string_buffer(len(ciphertext) + 16)
    first_length = ctypes.c_int()
    final_length = ctypes.c_int()
    try:
        if (
            crypto.EVP_DecryptInit_ex(
                context,
                crypto.EVP_aes_256_cbc(),
                None,
                key_buffer,
                iv_buffer,
            )
            != 1
        ):
            raise ProxyError("AES initialization failed")
        if (
            crypto.EVP_DecryptUpdate(
                context,
                output_buffer,
                ctypes.byref(first_length),
                input_buffer,
                len(ciphertext),
            )
            != 1
        ):
            raise ProxyError("AES decryption failed")
        final_pointer = ctypes.byref(output_buffer, first_length.value)
        if (
            crypto.EVP_DecryptFinal_ex(
                context,
                final_pointer,
                ctypes.byref(final_length),
            )
            != 1
        ):
            raise ProxyError("AES padding validation failed")
        return output_buffer.raw[
            : first_length.value + final_length.value
        ]
    finally:
        crypto.EVP_CIPHER_CTX_free(context)


def resolve_tracker_link(query: dict[str, list[str]]) -> str:
    links = query.get("link", [])
    files = query.get("file", [])
    if (
        len(links) != 1
        or not re.fullmatch(r"[A-Za-z0-9_-]{32,8192}", links[0])
        or len(files) != 1
        or not files[0]
    ):
        raise ProxyError("Prowlarr protected download link is invalid")
    key_row = database_row(
        'SELECT "Value" FROM "Config" WHERE lower("Key") = ?',
        ("downloadprotectionkey",),
    )
    if not key_row:
        raise ProxyError("Prowlarr download protection key is missing")
    key = str(key_row[0]).encode("utf-8")
    if len(key) != 32:
        raise ProxyError("Prowlarr download protection key is invalid")
    try:
        token = links[0]
        token += "=" * (-len(token) % 4)
        encrypted_base64 = base64.urlsafe_b64decode(token).decode("utf-8")
        full_cipher = base64.b64decode(encrypted_base64, validate=True)
        if len(full_cipher) <= 16 or (len(full_cipher) - 16) % 16:
            raise ValueError("invalid AES payload length")
        plain = aes_256_cbc_decrypt(
            key, full_cipher[:16], full_cipher[16:]
        )
        return plain.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as error:
        raise ProxyError("Prowlarr protected download link is invalid") from error


def rewrite_download_urls(xml_body: bytes, indexer_id: int) -> bytes:
    try:
        root = ElementTree.fromstring(xml_body)
    except ElementTree.ParseError as error:
        raise ProxyError("Prowlarr returned invalid Torznab XML") from error

    expected_path = f"/{indexer_id}/download"

    def rewrite(value: str | None) -> str | None:
        if not value:
            return value
        parsed = urllib.parse.urlsplit(value)
        if parsed.path != expected_path:
            return value
        return urllib.parse.urlunsplit(
            (*urllib.parse.urlsplit(PUBLIC_URL)[:2], parsed.path, parsed.query, "")
        )

    for element in root.iter():
        element.text = rewrite(element.text)
        for name, value in list(element.attrib.items()):
            element.attrib[name] = rewrite(value) or ""
    return ElementTree.tostring(
        root, encoding="utf-8", xml_declaration=True
    )


class ProxyHandler(BaseHTTPRequestHandler):
    server_version = "dothomelab-cross-seed-proxy/1.0"

    def log_message(self, format_string: str, *args: Any) -> None:
        LOGGER.info("client=%s status=%s", self.client_address[0], args[1])

    def send_body(
        self,
        status: int,
        body: bytes,
        content_type: str,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/health" and not parsed.query:
            try:
                api_key()
                if not PROWLARR_DB.is_file():
                    raise ProxyError("Prowlarr database is unavailable")
                ping = remote_request(
                    f"{PROWLARR_URL}/ping",
                    maximum=1024,
                )
                if ping.status != HTTPStatus.OK:
                    raise ProxyError("Prowlarr ping failed")
                self.send_body(HTTPStatus.OK, b"ok\n", "text/plain")
            except ProxyError:
                self.send_body(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    b"unhealthy\n",
                    "text/plain",
                )
            return

        match = PATH_PATTERN.fullmatch(parsed.path)
        if not match:
            self.send_body(HTTPStatus.NOT_FOUND, b"not found\n", "text/plain")
            return
        indexer_id = int(match.group(1))
        operation = match.group(2)
        query = urllib.parse.parse_qs(
            parsed.query, keep_blank_values=True
        )
        try:
            validate_api_key(query)
            context = indexer_context(indexer_id)
            if operation == "api":
                upstream = remote_request(
                    f"{PROWLARR_URL}{parsed.path}?{parsed.query}",
                    headers={
                        "Accept": "application/xml,application/rss+xml",
                        "User-Agent": self.headers.get(
                            "User-Agent", "cross-seed"
                        ),
                    },
                    maximum=MAX_TORZNAB_BYTES,
                )
                body = (
                    rewrite_download_urls(upstream.body, indexer_id)
                    if upstream.status == HTTPStatus.OK
                    else upstream.body
                )
                self.send_body(
                    upstream.status,
                    body,
                    upstream.headers.get(
                        "Content-Type", "application/rss+xml"
                    ),
                )
                return

            tracker_link = resolve_tracker_link(query)
            torrent = tracker_torrent(context, tracker_link)
            LOGGER.info(
                "served indexer=%s bytes=%s", indexer_id, len(torrent)
            )
            self.send_body(
                HTTPStatus.OK, torrent, "application/x-bittorrent"
            )
        except PermissionError:
            self.send_body(
                HTTPStatus.UNAUTHORIZED, b"unauthorized\n", "text/plain"
            )
        except (ProxyError, ValueError) as error:
            LOGGER.warning(
                "request failed indexer=%s operation=%s reason=%s",
                indexer_id,
                operation,
                error,
            )
            self.send_body(
                HTTPStatus.BAD_GATEWAY, b"upstream failure\n", "text/plain"
            )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
    LOGGER.info("listening port=%s", LISTEN_PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
