import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from worker import run


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.support = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        (self.support / 'vault/.obsidian').mkdir(parents=True)
        (self.support / 'config.json').write_text(json.dumps({
            'vault': str(self.support / 'vault'), 'host': 'fixture.invalid',
            'instagram_saved_url': 'https://www.instagram.com/fixture/saved/'}))
        self.path = self.support / 'worker-state.json'
        self.path.write_text(json.dumps({'retry': {}, 'yaay_scan': 99000, 'instagram_scan': 99000}))
        self.clock = self.stack.enter_context(patch('worker.time.time', return_value=100000))
        self.transport = self.stack.enter_context(patch('worker.Transport')).return_value
        self.pending = []
        self.catalog = {}
        self.transport.request.side_effect = self.request
        self.browser = self.stack.enter_context(patch('worker.open_browser'))
        self.stack.enter_context(patch('worker.sync_playwright'))
        self.stack.enter_context(patch('worker.fresh_context'))
        self.stack.enter_context(patch('worker.publish'))
        self.stack.enter_context(patch('worker.thumbnail'))
        self.stack.enter_context(patch('builtins.print'))
        self.yaay = self.stack.enter_context(patch('worker.collect_yaay', return_value=(
            {'status': 'complete', 'gaps': []}, {})))
        self.instagram = self.stack.enter_context(patch('worker.advance', side_effect=self.scan))
        self.download = self.stack.enter_context(patch('worker.download', side_effect=self.media))

    def request(self, header):
        if header['action'] == 'catalog':
            return self.catalog
        if header['action'] == 'pending':
            return list(self.pending)
        if header['action'] == 'complete_post':
            self.pending = [i for i in self.pending if i['source_key'] != header['source_key']]
        return {}

    def scan(self, *args, **kwargs):
        args[3].write_text('{}')
        return {'status': 'complete'}

    def media(self, url, cookies, work):
        file = work / '0.mp4'
        file.write_bytes(b'fixture')
        return [{'file': file, 'ordinal': 0}]

    def state(self, **changes):
        value = json.loads(self.path.read_text())
        if changes:
            value.update(changes)
            self.path.write_text(json.dumps(value))
        return value

    def test_backfill_switches_to_daily_and_skips_all_io_until_due(self):
        run(self.support, 12)
        self.assertTrue(self.state()['daily_mode'])
        self.assertEqual(self.state()['next_fetch_after'], 186400)
        requests = self.transport.request.call_count
        self.clock.return_value = 100600
        before = self.path.read_bytes()
        run(self.support, 12)
        self.assertEqual(self.transport.request.call_count, requests)
        self.assertEqual(self.browser.call_count, 1)
        self.assertEqual(self.path.read_bytes(), before)
        # An overdue wake/login produces one session, without replaying missed days.
        self.clock.return_value = 400000
        run(self.support, 12)
        self.yaay.assert_called_once()
        self.assertIsNone(self.instagram.call_args.kwargs['page_budget'])
        self.assertEqual(self.state()['next_fetch_after'], 486400)
        run(self.support, 12)
        self.yaay.assert_called_once()

    def test_explicit_collection_acquisition_keeps_daily_schedule_and_exact_membership(self):
        self.pending = [{'source_key': 'instagram:' + key, 'url': 'https://example.invalid/' + key}
                        for key in ['grind', 'elsewhere', 'removed']]
        self.catalog = {'collections': [{'source': 'instagram', 'id': 'g', 'active': 1}],
                        'items': [{'source': 'instagram', 'id': key, 'source_key': 'instagram:' + key}
                                  for key in ['grind', 'elsewhere', 'removed']],
                        'memberships': [{'source': 'instagram', 'collection_id': 'g', 'item_id': 'grind', 'active': 1},
                                        {'source': 'instagram', 'collection_id': 'g', 'item_id': 'removed', 'active': 0},
                                        {'source': 'yaay', 'collection_id': 'g', 'item_id': 'elsewhere', 'active': 1}]}
        self.state(daily_mode=True, next_fetch_after=186400)
        run(self.support, 45, 'g')
        self.assertEqual(self.state()['completed_this_run'], 1)
        self.assertEqual(self.state()['next_fetch_after'], 186400)
        self.assertEqual([p['source_key'] for p in self.pending], ['instagram:elsewhere', 'instagram:removed'])
        self.yaay.assert_not_called()
        self.instagram.assert_not_called()

    def test_failed_original_does_not_keep_frequent_polling_alive(self):
        self.pending = [{'source_key': 'instagram:unavailable', 'url': 'https://example.invalid/p'}]
        self.state(retry={'instagram:unavailable': {'after': 200000, 'attempts': 1}})
        run(self.support, 12)
        self.assertTrue(self.state()['daily_mode'])
        self.assertEqual(self.state()['pending_posts'], 1)
        self.assertIn('instagram:unavailable', self.state()['retry'])
        self.download.assert_not_called()

    def test_finish_attempts_each_pending_once_and_records_safe_failure_details(self):
        from downloader import DownloadError
        self.pending = [{'source_key': 'instagram:' + key, 'url': 'https://example.invalid/' + key}
                        for key in ['missing', 'one', 'two']]
        self.state(daily_mode=True, next_fetch_after=186400, acquisition_after=200000,
                   retry={'instagram:missing': {'after': 200000, 'attempts': 1}})
        def acquire(url, cookies, work):
            if url.endswith('/missing'):
                raise DownloadError(8, None, 0, [200, 404])
            return self.media(url, cookies, work)
        self.download.side_effect = acquire
        run(self.support, 1, finish=True)
        self.assertEqual(self.download.call_count, 3)
        self.assertEqual(self.state()['completed_this_run'], 2)
        self.assertEqual(self.state()['next_fetch_after'], 186400)
        self.assertIsNone(self.instagram.call_args.kwargs['page_budget'])
        self.yaay.assert_called_once()
        failure = self.state()['retry']['instagram:missing']
        self.assertEqual(failure['details'], {'exit': 8, 'expected': None, 'files': 0, 'http': [200, 404]})
        self.assertEqual(failure['reason'], 'source_download_incomplete')
        self.assertNotIn('url', failure)

    def test_finish_stops_on_rate_limiting(self):
        from downloader import DownloadError
        self.pending = [{'source_key': 'instagram:' + key, 'url': 'https://example.invalid/' + key}
                        for key in ['one', 'two']]
        self.download.side_effect = DownloadError(8, None, 0, [429])
        run(self.support, 45, finish=True)
        self.assertEqual(self.download.call_count, 1)
        self.assertEqual(self.state()['acquisition_after'], 103600)
        self.assertEqual(self.state()['retry']['instagram:one']['reason'], 'rate_limited')

    def test_unattempted_backlog_keeps_initial_batches(self):
        self.pending = [{'source_key': 'instagram:new', 'url': 'https://example.invalid/p'}]
        self.state(acquisition_after=200000)
        run(self.support, 12)
        self.assertFalse(self.state().get('daily_mode', False))

    def test_partial_inventory_does_not_switch_even_with_empty_queue(self):
        (self.support / 'instagram-scan.json').write_text('{}')
        self.instagram.side_effect = lambda *args, **kwargs: {'status': 'partial'}
        run(self.support, 12)
        self.assertFalse(self.state().get('daily_mode', False))
        self.assertEqual(self.instagram.call_args.kwargs['page_budget'], 8)

    def test_offline_daily_attempt_does_not_repeat_until_next_day(self):
        self.state(daily_mode=True, next_fetch_after=1)
        self.transport.request.side_effect = RuntimeError('offline fixture')
        with self.assertRaises(RuntimeError):
            run(self.support, 12)
        self.assertEqual(self.state()['next_fetch_after'], 186400)
        run(self.support, 12)
        self.transport.request.assert_called_once()
        self.browser.assert_not_called()

    def test_daily_batch_stays_daily_when_more_than_twelve_are_pending(self):
        self.state(daily_mode=True, next_fetch_after=1)
        self.pending = [{'source_key': f'instagram:{i}', 'url': f'https://example.invalid/{i}'} for i in range(13)]
        self.transport.put.return_value = {'id': 'a' * 64}
        run(self.support, 12)
        self.assertEqual(self.download.call_count, 12)
        self.assertEqual(self.state()['pending_posts'], 1)
        self.assertTrue(self.state()['daily_mode'])
        run(self.support, 12)
        self.assertEqual(self.download.call_count, 12)
        self.assertEqual(list((self.support / 'downloads').rglob('*.mp4')), [])


class InstallerTests(unittest.TestCase):
    def test_upgrade_reuses_private_settings_and_preserves_checkpoint_without_network(self):
        import install
        import plistlib
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            home = Path(folder).resolve()
            support = home / 'Library/Application Support/dothomelab-references'
            (support / 'venv/bin').mkdir(parents=True)
            (support / 'venv/bin/python').touch()
            (support / 'ingest-key').write_text('fixture only')
            (home / 'vault/.obsidian').mkdir(parents=True)
            config = {'vault': str(home / 'vault'), 'host': 'fixture.invalid',
                      'instagram_saved_url': 'https://www.instagram.com/fixture/saved/'}
            (support / 'config.json').write_text(json.dumps(config))
            (support / 'worker-state.json').write_text('{"pending_posts":626}')
            (support / 'instagram-scan.json').write_text('{"cursor":"fixture"}')
            stack.enter_context(patch('install.Path.home', return_value=home))
            stack.enter_context(patch('sys.argv', ['install.py', '--enable']))
            stack.enter_context(patch('install.subprocess.check_output', side_effect=['a' * 40, '']))
            commands = stack.enter_context(patch('install.subprocess.run', return_value=SimpleNamespace(returncode=0)))
            stack.enter_context(patch('builtins.print'))
            install.main()
            self.assertEqual(json.loads((support / 'config.json').read_text()), config)
            self.assertEqual((support / 'worker-state.json').read_text(), '{"pending_posts":626}')
            self.assertEqual((support / 'instagram-scan.json').read_text(), '{"cursor":"fixture"}')
            plist = plistlib.loads((home / 'Library/LaunchAgents/media.rafael.reference-collector.plist').read_bytes())
            self.assertIn(str(support / 'releases' / ('a' * 40) / 'worker.py'), plist['ProgramArguments'])
            self.assertTrue(any(c.args[0][:2] == ['launchctl', 'bootstrap'] for c in commands.call_args_list))
            self.assertFalse(any(c.args[0][0] == 'ssh' for c in commands.call_args_list))
