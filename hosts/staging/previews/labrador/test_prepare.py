import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('prepare', Path(__file__).with_name('prepare.py'))
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class RecipeTests(unittest.TestCase):
    def test_manifest_preserves_long_dependency_classpath(self):
        names = ['a' * 64 + '-spring-core.jar', 'b' * 64 + '-spring-context.jar']
        data = prepare.manifest_bytes('example.Main', names)
        self.assertTrue(all(len(line) <= 70 for line in data.split(b'\r\n')))
        unfolded = data.replace(b'\r\n ', b'').decode()
        self.assertIn('Class-Path: ' + ' '.join('lib/' + name for name in names), unfolded)
        self.assertTrue(data.endswith(b'\r\n\r\n'))

    def test_package_contains_current_classes_without_old_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / 'classes/META-INF').mkdir(parents=True)
            (output / 'classes/META-INF/MANIFEST.MF').write_text('old')
            (output / 'classes/Current.class').write_bytes(b'current')
            (output / 'classes/example/security').mkdir(parents=True)
            (output / 'classes/example/security/Config.class').write_bytes(b'config')
            prepare.package_app(output, 'example.Main', ['one.jar'])
            with zipfile.ZipFile(output / 'context/build/libs/application.jar') as archive:
                self.assertEqual(archive.read('Current.class'), b'current')
                self.assertEqual(archive.namelist().count('META-INF/MANIFEST.MF'), 1)
                self.assertIn('example/', archive.namelist())
                self.assertIn('example/security/', archive.namelist())
                self.assertIn(b'Main-Class: example.Main', archive.read('META-INF/MANIFEST.MF'))

    def test_recipe_refuses_unrecognized_upstream_startup(self):
        with self.assertRaises(ValueError):
            prepare.change('CMD another-launcher', r'^RUN git clone .*$', 'COPY artifact')

    def test_core_build_uses_only_manifest_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            java = source / 'src/main/java'
            java.mkdir(parents=True)
            (java / 'Main.java').write_text('class Main {}')
            (java / '._Main.java').write_bytes(b'archive metadata')
            (source / 'build.gradle.kts').write_text('version = "1"')
            artifact_manifest = {'coreSource': {'src/main/java/Main.java': 'hash'},
                                 'dependencies': {'core': []}}
            with patch.object(prepare, 'builder'):
                prepare.compile_app(source, root / 'output', root, 'core', artifact_manifest, 'jdk')
            args = (root / 'output/sources.txt').read_text()
            self.assertIn('/source/src/main/java/Main.java', args)
            self.assertNotIn('._Main.java', args)

    def test_override_replaces_published_ports_and_preserves_data(self):
        text = prepare.overlay(Path('/previews/one'), Path('/previews/one/source'),
                               19000, '192.168.0.114', 'branchline-skills:one', '2g', 2)
        self.assertEqual(text.count('ports: !override'), 3)
        self.assertIn('192.168.0.114:19000:8084', text)
        self.assertIn('/previews/one/mysql:/var/lib/mysql', text)
        self.assertIn('/preview-state', text)
        self.assertIn('--lower-case-table-names=1', text)
        self.assertIn('SPRING_JPA_HIBERNATE_DDL_AUTO: "none"', text)
        self.assertEqual(text.count('cap_drop: [ALL]'), 3)


if __name__ == '__main__':
    unittest.main()
