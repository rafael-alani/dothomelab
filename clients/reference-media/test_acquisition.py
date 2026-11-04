import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from downloader import DownloadError
from worker import acquire, download_yaay, media_extension

MP4 = b'\x00\x00\x00\x20ftypisom' + b'fixture'


class AcquisitionTests(unittest.TestCase):
    def test_unavailable_original_uses_the_same_identitys_yaay_copy(self):
        item = {'source_key': 'instagram:ABC', 'url': 'https://instagram.com/p/ABC/'}
        context = Mock()
        context.request.get.return_value = Mock(ok=True, headers={'content-type': 'video/mp4'},
                                                body=lambda: MP4)
        media = {'instagram:ABC': [{'url': 'https://media.invalid/saved.mp4', 'ordinal': 0, 'kind': 'video'}]}
        with tempfile.TemporaryDirectory() as directory, patch('worker.download', side_effect=DownloadError(8, None, 0, [404])), \
                patch('worker.subprocess.run', return_value=Mock(returncode=0, stdout=b'{"streams":[{"codec_type":"video"}],"format":{"duration":"12"}}')):
            files, via = acquire(item, [], context, media, Path(directory))
            self.assertEqual(via, 'yaay')
            self.assertEqual(files[0]['ordinal'], 0)
            self.assertEqual(files[0]['file'].read_bytes(), MP4)
        context.request.get.return_value.dispose.assert_called_once()

    def test_rate_limit_is_not_hidden_by_fallback(self):
        context = Mock()
        with tempfile.TemporaryDirectory() as directory, patch('worker.download', side_effect=DownloadError(8, None, 0, [429])):
            with self.assertRaises(DownloadError):
                acquire({'source_key': 'instagram:ABC', 'url': 'https://instagram.com/p/ABC/'}, [], context,
                        {'instagram:ABC': [{'url': 'https://media.invalid/copy', 'ordinal': 0}]}, Path(directory))
        context.request.get.assert_not_called()

    def test_missing_member_or_thumbnail_for_video_cannot_complete(self):
        context = Mock()
        response = context.request.get.return_value = Mock(ok=True, headers={'content-type': 'image/jpeg'}, body=lambda: b'fixture')
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'yaay_member_unavailable'):
                download_yaay(context, [{'url': None, 'ordinal': 0}], Path(directory))
            with self.assertRaisesRegex(ValueError, 'unsupported_yaay_media'):
                download_yaay(context, [{'url': 'https://media.invalid/thumb.jpg', 'ordinal': 0, 'kind': 'video'}], Path(directory))
        response.dispose.assert_called_once()

    def test_generic_or_missing_cdn_header_requires_real_media_signature(self):
        for header in ('', 'application/octet-stream', 'video/mp4'):
            self.assertEqual(media_extension(MP4, header, 'video'), 'mp4')
        self.assertEqual(media_extension(b'\xff\xd8\xfffixture', 'application/octet-stream', 'image'), 'jpg')
        for body, header, kind in [(b'<html>error</html>', '', 'video'),
                                   (b'\xff\xd8\xffthumbnail', '', 'video'),
                                   (MP4, 'image/jpeg', 'video'), (MP4, '', 'image')]:
            with self.assertRaisesRegex(ValueError, 'unsupported_yaay_media'):
                media_extension(body, header, kind)

    def test_mp4_signature_without_a_playable_video_does_not_complete(self):
        context = Mock()
        context.request.get.return_value = Mock(ok=True, headers={}, body=lambda: MP4)
        with tempfile.TemporaryDirectory() as directory, patch('worker.subprocess.run', return_value=Mock(returncode=0, stdout=b'{"streams":[]}')):
            with self.assertRaisesRegex(ValueError, 'invalid_yaay_video'):
                download_yaay(context, [{'url': 'https://media.invalid/copy', 'ordinal': 0, 'kind': 'video'}], Path(directory))
        context.request.get.return_value.dispose.assert_called_once()
