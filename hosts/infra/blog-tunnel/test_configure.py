import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import configure as subject


class ConfigurationTests(unittest.TestCase):
    def test_token_is_scoped_to_declared_account_and_tunnel(self):
        data = {"a": subject.DECLARED["account_id"], "t": subject.DECLARED["tunnel_id"], "s": "fixture"}
        encode = lambda value: base64.b64encode(json.dumps(value).encode()).decode()
        subject.validate_token(encode(data))
        for invalid in ("not-a-token", encode({**data, "a": "other"}), encode({**data, "t": "other"}), encode({**data, "s": ""})):
            with self.assertRaises(ValueError):
                subject.validate_token(invalid)

    def test_env_edit_preserves_unrelated_values_and_comments(self):
        text = "# retained\nPASSWORD='literal $() # spaces'\nDOMAINS=rafael.ink,pictures.rafael.ink\n"
        actual = subject.replace_value(text, "DOMAINS", "pictures.rafael.ink")
        self.assertEqual(actual, "# retained\nPASSWORD='literal $() # spaces'\nDOMAINS=pictures.rafael.ink\n")
        with self.assertRaises(ValueError):
            subject.replace_value("DOMAINS=a\nDOMAINS=b\n", "DOMAINS", "c")
        with self.assertRaises(ValueError):
            subject.replace_value(text, "DOMAINS", "a\nSECRET=oops")

    def test_ddns_removes_exact_apex_only(self):
        self.assertEqual(subject.without_apex("pictures.rafael.ink,rafael.ink,stream.rafael.ink"),
                         "pictures.rafael.ink,stream.rafael.ink")
        self.assertEqual(subject.without_apex("pictures.rafael.ink"), "pictures.rafael.ink")
        for domains in ("rafael.ink", "*.rafael.ink,rafael.ink"):
            with self.assertRaises(ValueError):
                subject.without_apex(domains)

    def test_dns_refuses_multiple_address_records(self):
        with patch.object(subject, "api", side_effect=[[{"id": "zone"}],
                [{"type": "A"}, {"type": "AAAA"}]]):
            with self.assertRaises(ValueError):
                subject.apex_record()

    def test_record_update_preserves_dns_metadata_not_api_fields(self):
        record = {"id": "record", "type": "A", "name": "rafael.ink", "content": "192.0.2.1",
                  "proxied": True, "ttl": 1, "comment": "keep", "tags": ["owner:blog"], "created_on": "old"}
        body = subject.record_body(record)
        self.assertEqual(body["tags"], ["owner:blog"])
        self.assertEqual(body["comment"], "keep")
        self.assertNotIn("id", body)
        self.assertNotIn("created_on", body)

    def test_cutover_rejects_dns_drift_and_apex_still_in_ddns(self):
        original = {"type": "A", "name": "rafael.ink", "content": "192.0.2.1", "ttl": 1, "proxied": True}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "dns.json").write_text(json.dumps({"zone": "zone", "record_id": "record", "record": original,
                                                      "domains": "rafael.ink,pictures.rafael.ink"}))
            for record, domains in (({**original, "content": "192.0.2.2"}, "pictures.rafael.ink"),
                                    (original, "rafael.ink,pictures.rafael.ink")):
                with patch.object(subject, "ROLLBACK", root), \
                     patch.object(subject, "apex_record", return_value=("zone", {**record, "id": "record"})), \
                     patch.object(subject, "parse", return_value=[("DOMAINS", domains)]), \
                     patch.object(subject, "api") as api, patch.object(subject, "run") as run:
                    with self.assertRaises(ValueError):
                        subject.switch_dns()
                    api.assert_not_called()
                    run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
