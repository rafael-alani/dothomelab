import subprocess
import unittest
from unittest.mock import patch
import run


class ExportLifetimeTests(unittest.TestCase):
    def test_existing_detached_export_prevents_a_second_writer(self):
        with patch.object(run.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'existing-id\n')) as command:
            run.run_export(['docker', 'compose'])
        self.assertEqual(command.call_count, 1)

    def test_export_has_a_known_name_and_full_execution_budget(self):
        with patch.object(run.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '')) as command:
            run.run_export(['docker', 'compose'])
        invocation = command.call_args_list[1]
        self.assertIn('dothomelab-blog-export', invocation.args[0])
        self.assertEqual(invocation.kwargs['timeout'], 600)

    def test_timeout_stops_only_the_named_disposable_export(self):
        expired = subprocess.TimeoutExpired('docker compose run', 600)
        with patch.object(run.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0, ''), expired, subprocess.CompletedProcess([], 0)]) as command:
            with self.assertRaises(subprocess.TimeoutExpired):
                run.run_export(['docker', 'compose'])
        self.assertEqual(command.call_args_list[-1].args[0], ['docker', 'stop', '--time', '30', 'dothomelab-blog-export'])


if __name__ == '__main__':
    unittest.main()
