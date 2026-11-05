"""Exercise the policy without Docker or production credentials."""
import os
from pathlib import Path
import subprocess
import unittest

POLICY = Path(__file__).with_name('policy.sh')


class PolicyTest(unittest.TestCase):
    def run_policy(self, **values):
        env = {k: v for k, v in os.environ.items() if not k.startswith('PAPERLESS_GPT_')}
        return subprocess.run(
            ['bash', '-c', 'source "$1"; validate_paperless_gpt_policy || exit $?; '
             'if paperless_gpt_enabled; then echo enabled; else echo disabled; fi', '_', str(POLICY)],
            env={**env, **values}, text=True, capture_output=True,
        )

    def test_absent_or_disabled_needs_no_external_key(self):
        for values in [{}, {'PAPERLESS_GPT_ENABLED': 'false'}]:
            result = self.run_policy(**values)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), 'disabled')

    def test_enabled_rejects_missing_and_placeholder_key(self):
        for key in ['', 'replace-with-openai-api-key']:
            result = self.run_policy(PAPERLESS_GPT_ENABLED='true', PAPERLESS_GPT_OPENAI_API_KEY=key)
            self.assertNotEqual(result.returncode, 0)

    def test_enabled_accepts_provided_key_without_printing_it(self):
        key = 'test-only-never-a-production-key'
        result = self.run_policy(PAPERLESS_GPT_ENABLED='true', PAPERLESS_GPT_OPENAI_API_KEY=key)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'enabled')
        self.assertNotIn(key, result.stdout + result.stderr)

    def test_typo_does_not_silently_disable(self):
        self.assertNotEqual(self.run_policy(PAPERLESS_GPT_ENABLED='treu').returncode, 0)


if __name__ == '__main__':
    unittest.main()
