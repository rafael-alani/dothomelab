#!/usr/bin/env python3
"""Keep ordinary preview routes on CT114; allow only the declared Apps move."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('configure_routes', Path(__file__).with_name('configure-routes.py'))
routes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routes)


class RouteTests(unittest.TestCase):
    def test_default_staging_target_and_collision_protection(self):
        app = {'hostname': 'blog.staging.rafael.media'}
        self.assertEqual(routes.check_existing_route(app, [(1, '192.168.0.114')]), '192.168.0.114')
        with self.assertRaises(RuntimeError):
            routes.check_existing_route(app, [(1, '192.168.0.112')])

    def test_shared_routes_move_and_rerun_on_apps(self):
        for hostname in routes.SHARED_OBSERVABILITY_HOSTNAMES:
            app = {'hostname': hostname, 'forward_host': '192.168.0.112'}
            for existing in ([], [(1, '192.168.0.114')], [(1, '192.168.0.112')]):
                self.assertEqual(routes.check_existing_route(app, existing), '192.168.0.112')
            for invalid in ([(1, '192.168.0.110')], [(1, '192.168.0.114'), (2, '192.168.0.112')]):
                with self.assertRaises(RuntimeError):
                    routes.check_existing_route(app, invalid)

    def test_arbitrary_upstream_and_unrelated_app_fail_closed(self):
        for app in ({'hostname': 'blog.staging.rafael.media', 'forward_host': '192.168.0.112'},
                    {'hostname': 'analytics.staging.rafael.media', 'forward_host': 'example.com'}):
            with self.assertRaises(RuntimeError):
                routes.route_upstream(app)


if __name__ == '__main__':
    unittest.main()
