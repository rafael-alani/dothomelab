import io
import unittest
import urllib.error
from unittest.mock import patch

from configure import reconcile_path_mappings, request


class ConfigurationTests(unittest.TestCase):
    def test_mapping_repairs_navidrome_and_preserves_other_integrations(self):
        other = {'source': 'jellyfin', 'remote': '/audio', 'local': '/readonly/audio'}
        old = [{'source': 'navidrome', 'remote': '/music', 'local': '/wrong'}, other]
        result = reconcile_path_mappings(old)
        self.assertIn({'source': 'navidrome', 'remote': '/music', 'local': '/data/media/music'}, result)
        self.assertIn(other, result)
        self.assertEqual(reconcile_path_mappings(result), result)
        self.assertEqual(old[0]['local'], '/wrong')

    def test_http_errors_do_not_disclose_query_credentials_or_response_body(self):
        error = urllib.error.HTTPError('http://example.invalid/?apiKey=secret', 401, 'bad', {}, io.BytesIO(b'secret'))
        with patch('urllib.request.urlopen', side_effect=error):
            with self.assertRaisesRegex(RuntimeError, '^Aurral GET /test returned HTTP 401$'):
                request('/test?apiKey=secret')


if __name__ == '__main__':
    unittest.main()
