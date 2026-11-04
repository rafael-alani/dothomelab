"""Maintained gallery-dl acquisition with in-memory browser authentication."""
import logging
from pathlib import Path
from gallery_dl import config, job


class DownloadError(RuntimeError):
    def __init__(self, status, expected, files, responses):
        self.details = {'exit': status, 'expected': expected, 'files': files,
                        'http': sorted(set(responses))}
        self.reason = ('rate_limited' if 429 in responses else
                       'source_access_denied' if any(code in responses for code in (401, 403)) else
                       'source_download_incomplete')
        super().__init__(self.reason)


def configure(cookies, directory=None):
    # Third-party debug/HTTP logs can include session tokens and signed URLs.
    logging.disable(logging.CRITICAL)
    config.clear()
    config.set(('output',), 'mode', 'null')
    config.set(('extractor',), 'retries', 1)
    config.set(('extractor',), 'timeout', 30)
    config.set(('extractor', 'instagram'), 'cookies', {c['name']: c['value'] for c in cookies if c['domain'].lstrip('.') == 'instagram.com'})
    config.set(('extractor', 'instagram'), 'videos', 'merged')
    config.set(('extractor', 'instagram'), 'previews', False)
    if directory:
        config.set(('extractor',), 'base-directory', str(directory))
        config.set(('extractor',), 'directory', [])
        config.set(('extractor',), 'filename', '{num:03}.{extension}')


def download(url, cookies, directory):
    configure(cookies, directory)
    task = job.DownloadJob(url)
    task.expected = None
    responses = []
    task.extractor.initialize()
    parse_post = task.extractor._parse_post
    def parse_media(post):
        metadata = parse_post(post)
        # gallery-dl's count includes optional separate music-track files. The
        # board archive includes every image/video member, not separate audio.
        task.expected = sum(not member.get('audio_url') for member in metadata['_files'])
        return metadata
    task.extractor._parse_post = parse_media
    task.extractor.session.hooks['response'].append(lambda response, *args, **kwargs: responses.append(response.status_code))
    status = task.run()
    files = sorted(p for p in Path(directory).iterdir() if p.is_file() and p.suffix.lower() in {'.mp4', '.webm', '.mov', '.jpg', '.jpeg', '.png', '.webp'})
    if status or not files or task.expected != len(files):
        raise DownloadError(status, task.expected, len(files), responses)
    return [{'file': file, 'ordinal': int(file.stem) - 1} for file in files]
