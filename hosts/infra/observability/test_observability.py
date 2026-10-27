import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('fleet', HERE / 'collect-fleet.py')
fleet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fleet)


class FleetTests(unittest.TestCase):
    def row(self):
        return {'type': 'app-container', 'name': 'staging-blog-web-1', 'status': 'online',
            'lastSeen': '2026-10-27T00:00:00Z',
            'metrics': {'cpu': {'percent': 2}, 'memory': {'used': 100, 'total': 200, 'percent': 50}},
            'docker': {'hostname': 'staging', 'containerState': 'running', 'health': 'healthy', 'secret': 'DO_NOT_EXPORT',
                'labels': {'com.docker.compose.project': 'staging-blog',
                           'com.docker.compose.service': 'web', 'credential': 'DO_NOT_EXPORT'}}}

    def test_shared_identity_and_strict_field_allowlist(self):
        row = self.row()
        now = fleet.timestamp(row['lastSeen']) + 10
        text, state, events = fleet.render([row], {}, now)
        self.assertIn('project="blog"', text)
        self.assertIn('environment="staging"', text)
        self.assertIn('guest_id="114"', text)
        self.assertIn('resource_memory_used_bytes', text)
        self.assertNotIn('DO_NOT_EXPORT', text + json.dumps(state) + json.dumps(events))
        self.assertEqual(len(events), 1)
        self.assertEqual(fleet.render([row], state, now + 1)[2], [])

    def test_stale_values_are_absent_and_state_change_is_reported(self):
        row = self.row()
        now = fleet.timestamp(row['lastSeen'])
        _, previous, _ = fleet.render([row], {}, now)
        text, _, events = fleet.render([row], previous, now + 181)
        self.assertNotIn('resource_memory_used_bytes', text)
        self.assertIn('resource_fresh', text)
        self.assertEqual(events[0]['fresh'], False)

    def test_environment_and_guest_remain_separate(self):
        staging = self.row()
        production = self.row()
        production['name'] = 'production-blog-web-1'
        production['docker'] = {**production['docker'], 'hostname': 'production'}
        self.assertNotEqual(fleet.identity(staging), fleet.identity(production))

    def test_missing_numeric_value_is_not_zero(self):
        row = self.row()
        row['metrics'] = {'cpu': {'percent': float('nan')}}
        text, _, _ = fleet.render([row], {}, fleet.timestamp(row['lastSeen']))
        self.assertNotIn('resource_cpu_percent', text)

    def test_exited_container_is_not_running_despite_pulse_online_status(self):
        row = self.row()
        row['docker'].update(containerState='exited', health='unhealthy')
        text, state, _ = fleet.render([row], {}, fleet.timestamp(row['lastSeen']))
        self.assertEqual(next(iter(state.values()))['status'], 'offline')
        self.assertNotIn('resource_healthy', text)
        self.assertNotIn('resource_memory_used_bytes', text)

    def test_duplicate_identity_fails_before_replacing_export(self):
        row = self.row()
        with self.assertRaises(ValueError):
            fleet.render([row, row], {}, fleet.timestamp(row['lastSeen']))


if __name__ == '__main__':
    unittest.main()
