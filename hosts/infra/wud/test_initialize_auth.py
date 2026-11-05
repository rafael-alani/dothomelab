import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('initialize_auth', Path(__file__).with_name('initialize-auth.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AuthenticationTest(unittest.TestCase):
    def test_missing_credential_is_retained_without_rewriting_other_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'dotenv'
            original = "OTHER='literal # value'\nWUD_ADMIN_PASSWORD=\n"
            path.write_text(original)
            password = module.ensure_password(path)
            self.assertEqual(len(password), 64)
            self.assertTrue(path.read_text().startswith(original))
            once = path.read_text()
            self.assertEqual(module.ensure_password(path), password)
            self.assertEqual(path.read_text(), once)

    def test_existing_weak_credential_is_rejected_without_rotation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'dotenv'
            path.write_text('WUD_ADMIN_PASSWORD=existing\n')
            with self.assertRaises(ValueError):
                module.ensure_password(path)
            self.assertEqual(path.read_text(), 'WUD_ADMIN_PASSWORD=existing\n')


if __name__ == '__main__':
    unittest.main()
