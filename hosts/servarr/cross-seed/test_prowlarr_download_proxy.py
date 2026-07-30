#!/usr/bin/env python3
"""Focused tests for the private Prowlarr download compatibility proxy."""

from __future__ import annotations

import importlib.util
import sys
import unittest
import urllib.parse
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).with_name("prowlarr-download-proxy.py")
SPEC = importlib.util.spec_from_file_location(
    "prowlarr_download_proxy", MODULE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load the proxy module")
proxy = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = proxy
SPEC.loader.exec_module(proxy)

VALID_TORRENT = (
    b"d8:announce14:https://x.test4:infod4:name1:xee"
)


class ProxyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = proxy.IndexerContext(
            indexer_id=33,
            definition="dothomelab-btschool",
            base_url="https://tracker.example/",
            cookies={"session": "opaque"},
        )

    def test_validates_bounded_torrent_dictionary(self) -> None:
        proxy.validate_bencoded_torrent(VALID_TORRENT)
        with self.assertRaisesRegex(proxy.ProxyError, "invalid"):
            proxy.validate_bencoded_torrent(b"<html>not a torrent</html>")

    def test_submits_exact_download_notice_and_returns_torrent(self) -> None:
        notice = b"""
        <form action="?" method="post">
          <input type="hidden" name="id" value="42">
          <input type="hidden" name="type" value="firsttime">
          <input id="continuedownload" type="checkbox"
                 name="hidenotice" value="1" checked>
          <input type="submit" name="submit" value="confirm">
        </form>
        """
        responses = [
            proxy.RemoteResponse(
                status=200,
                headers={"Content-Type": "text/html; charset=utf-8"},
                body=notice,
            ),
            proxy.RemoteResponse(
                status=302,
                headers={"Content-Type": "application/x-bittorrent"},
                body=VALID_TORRENT,
            ),
        ]
        with mock.patch.object(
            proxy, "remote_request", side_effect=responses
        ) as request:
            result = proxy.tracker_torrent(
                self.context,
                "https://tracker.example/download.php?id=42",
            )

        self.assertEqual(result, VALID_TORRENT)
        self.assertEqual(request.call_count, 2)
        post = request.call_args_list[1]
        self.assertEqual(post.args[0], "https://tracker.example/download.php?id=42")
        self.assertEqual(post.kwargs["method"], "POST")
        self.assertFalse(post.kwargs["follow_redirects"])
        self.assertEqual(
            urllib.parse.parse_qs(post.kwargs["data"].decode()),
            {
                "id": ["42"],
                "type": ["firsttime"],
                "hidenotice": ["1"],
                "submit": ["confirm"],
            },
        )

    def test_rejects_non_download_path_before_network_request(self) -> None:
        with mock.patch.object(proxy, "remote_request") as request:
            with self.assertRaisesRegex(proxy.ProxyError, "allowlist"):
                proxy.tracker_torrent(
                    self.context,
                    "https://tracker.example/profile.php?id=42",
                )
        request.assert_not_called()

    def test_rewrites_only_selected_prowlarr_download_urls(self) -> None:
        original_public_url = proxy.PUBLIC_URL
        proxy.PUBLIC_URL = "http://gluetun:9697"
        try:
            result = proxy.rewrite_download_urls(
                b"""<?xml version="1.0"?>
                <rss><channel><item>
                  <link>http://prowlarr:9696/33/download?link=opaque&amp;file=x</link>
                  <comments>http://prowlarr:9696/33/api?t=details</comments>
                </item></channel></rss>""",
                33,
            )
        finally:
            proxy.PUBLIC_URL = original_public_url

        root = ElementTree.fromstring(result)
        link = root.findtext("./channel/item/link")
        comments = root.findtext("./channel/item/comments")
        self.assertEqual(
            link,
            "http://gluetun:9697/33/download?link=opaque&file=x",
        )
        self.assertEqual(
            comments, "http://prowlarr:9696/33/api?t=details"
        )


if __name__ == "__main__":
    unittest.main()
