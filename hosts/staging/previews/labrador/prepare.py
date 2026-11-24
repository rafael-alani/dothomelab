#!/usr/bin/env python3
"""Adapt the repository's E2E Compose stack to an isolated, exact-source preview.

The dependency bundle is an explicit offline build input, never a source of app
classes. Both applications are compiled from source; project Gradle repositories
and the original Dockerfile's GitLab clone are never contacted.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import zipfile


HERE = Path(__file__).resolve().parent
BUILDERS = set()
ADMIN_FIXTURE = """USE labracore;
START TRANSACTION;
SET @preview_admin_id = (SELECT id FROM concrete_person WHERE username = 'admin1');
INSERT INTO person (id) SELECT NULL WHERE @preview_admin_id IS NULL;
INSERT INTO concrete_person
    (id, username, display_name, number, email, external_id, default_role, account_disabled, two_fa_enabled)
SELECT LAST_INSERT_ID(), 'admin1', 'Admin 1', 900001, 'admin1@tudelft.nl', 'admin1', 5, 0, 0
WHERE @preview_admin_id IS NULL;
COMMIT;
"""


def preview_seed(source, directory):
    seed = directory / 'core-seed'
    shutil.copytree(source / 'end_to_end/src/test/resources/mysql/1_after_labracore',
                    seed, dirs_exist_ok=True)
    (seed / '99_preview_admin.sql').write_text(ADMIN_FIXTURE)


def stop_builders(*_):
    for name in list(BUILDERS):
        subprocess.run(['docker', 'stop', '--time', '1', name], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=5)
    if _:
        raise SystemExit(128 + _[0])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*command, cwd=None):
    subprocess.run(command, cwd=cwd, check=True)


def change(text, pattern, replacement):
    result, count = re.subn(pattern, replacement, text, flags=re.M)
    if count != 1:
        raise ValueError('Unsupported application Dockerfile: expected one ' + pattern)
    return result


def checked_artifacts(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    for app, entries in manifest['dependencies'].items():
        for entry in entries:
            if digest(root / 'dependencies' / app / entry['name']) != entry['sha256']:
                raise ValueError('Dependency checksum mismatch: ' + entry['name'])
    for name, expected in manifest['coreSource'].items():
        if digest(root / 'core-source' / name) != expected:
            raise ValueError('LabraCore source checksum mismatch: ' + name)
    return manifest


def manifest_bytes(main, libraries):
    # JAR manifests require byte-wrapped continuation lines, including Class-Path.
    lines = ['Manifest-Version: 1.0', 'Main-Class: ' + main,
             'Class-Path: ' + ' '.join('lib/' + name for name in libraries)]
    output = bytearray()
    for line in lines:
        data = line.encode('utf-8')
        output += data[:70] + b'\r\n'
        data = data[70:]
        while data:
            output += b' ' + data[:69] + b'\r\n'
            data = data[69:]
    return bytes(output) + b'\r\n'


def builder(image, mounts, command, network='none', memory='2g'):
    name = 'bl-build-' + secrets.token_hex(8)
    args = ['docker', 'run', '--rm', '--name', name, '--network', network, '--cpus=2',
            '--memory=' + memory, '--pids-limit=256', '--cap-drop=ALL',
            '--security-opt=no-new-privileges', '--user=0:0']
    args += ['--label', 'io.branchline.preview=' + os.environ['BRANCHLINE_PREVIEW_ID']]
    for source, target, readonly in mounts:
        args += ['--mount', f'type=bind,source={source},target={target}' + (',readonly' if readonly else '')]
    BUILDERS.add(name)
    try:
        run(*args, image, *command)
    finally:
        subprocess.run(['docker', 'stop', '--time', '1', name], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=5)
        BUILDERS.discard(name)


def compile_app(source, output, artifacts, app, manifest, java_image):
    classes = output / 'classes'
    classes.mkdir(parents=True, exist_ok=True)
    sources = sorted(source / name for name in manifest['coreSource'] if name.startswith('src/main/java/') and name.endswith('.java')) if app == 'core' else sorted((source / 'src/main/java').rglob('*.java'))
    if not sources:
        raise ValueError('No Java sources for ' + app)
    names = [entry['name'] for entry in manifest['dependencies'][app]]
    source_args = ['"/source/' + str(p.relative_to(source)).replace('\\', '\\\\').replace('"', '\\"') + '"' for p in sources]
    if any('\n' in name or '\r' in name for name in source_args):
        raise ValueError('Newlines in Java source paths are not supported')
    (output / 'sources.txt').write_text('\n'.join(source_args) + '\n')
    libraries = ':'.join('/dependencies/' + name for name in names)
    builder(java_image, [(source, '/source', True), (output, '/output', False),
                        (artifacts / 'dependencies' / app, '/dependencies', True)],
            ['javac', '-J-Xmx1024m', '--release', '21', '-parameters', '-Xmaxwarns', '3',
             '-cp', libraries, '-d', '/output/classes', '@/output/sources.txt'])
    resources = [source / name for name in manifest['coreSource'] if name.startswith('src/main/resources/')] if app == 'core' else (source / 'src/main/resources').rglob('*')
    for resource in resources:
        if resource.is_file() and not resource.name.startswith('application'):
            destination = classes / resource.relative_to(source / 'src/main/resources')
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(resource, destination)
    version = re.search(r'^version\s*=\s*"([^"]+)"', (source / 'build.gradle.kts').read_text(), re.M)
    meta = classes / 'META-INF/build-info.properties'
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(f'build.artifact={app}\nbuild.name={app}\nbuild.version={version.group(1) if version else "preview"}\n')
    libdir = output / 'context/build/preview-libs'
    libdir.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copy2(artifacts / 'dependencies' / app / name, libdir / name)
    return names


def package_app(output, main, libraries):
    jar = output / 'context/build/libs/application.jar'
    jar.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(jar, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('META-INF/MANIFEST.MF', manifest_bytes(main, libraries))
        for resource in sorted((output / 'classes').rglob('*')):
            # Spring discovers package roots through directory resources. JARs
            # with class files alone load Main but silently lose component scans.
            if resource.is_dir():
                archive.write(resource, str(resource.relative_to(output / 'classes')) + '/')
            elif resource.is_file() and str(resource.relative_to(output / 'classes')) != 'META-INF/MANIFEST.MF':
                archive.write(resource, str(resource.relative_to(output / 'classes')))


def frontend(source, output, node_image):
    target = output / 'frontend'
    shutil.copytree(source / 'frontend', target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('node_modules', 'build', 'dist', '.env*', '.npmrc'))
    lock = json.loads((target / 'package-lock.json').read_text())
    for entry in lock.get('packages', {}).values():
        resolved = entry.get('resolved', '')
        if resolved and not resolved.startswith('https://registry.npmjs.org/'):
            raise ValueError('Frontend dependency is outside the approved public npm registry')
    assets = output / 'frontend-assets'
    assets.mkdir(exist_ok=True)
    mounts = [(target, '/frontend', False), (assets, '/assets', False)]
    builder(node_image, mounts, ['npm', '--prefix', '/frontend', 'ci', '--ignore-scripts',
                                '--no-audit', '--no-fund', '--userconfig=/dev/null',
                                '--registry=https://registry.npmjs.org'], network='bridge')
    builder(node_image, mounts, ['sh', '-c', 'cd /frontend && node node_modules/vite/bin/vite.js build --outDir /assets'])
    shutil.copytree(assets, output / 'classes/static', dirs_exist_ok=True)


def overlay(directory, source, port, bind, image, memory, cpus, database_image='mysql:9.0.1'):
    # !override replaces fixed upstream ports instead of appending a second bind.
    return f'''services:
  database:
    image: {json.dumps(database_image)}
    # Historical migrations mix table-name case; use a fresh, explicitly
    # case-insensitive preview database without changing application commits.
    command: ["--lower-case-table-names=1"]
    ports: !override []
    environment:
      MYSQL_ALLOW_EMPTY_PASSWORD: null
      MYSQL_ROOT_PASSWORD: ${{PREVIEW_DB_ROOT_PASSWORD:?}}
    volumes:
      - {json.dumps(str(directory / 'mysql') + ':/var/lib/mysql')}
      - {json.dumps(str(source / 'end_to_end/src/test/resources/mysql/0_before_start') + ':/docker-entrypoint-initdb.d:ro')}
    user: "999:999"
    restart: unless-stopped
    mem_limit: 768m
    cpus: 1
    pids_limit: 256
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    labels:
      wud.watch: "false"
  jaeger:
    profiles: [tracing]
    ports: !override []
    mem_limit: 256m
    cpus: 0.5
    pids_limit: 128
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    labels:
      wud.watch: "false"
  skills:
    image: {image}
    ports: !override
      - {json.dumps(f'{bind}:{port}:8084')}
    links: !override [database]
    environment:
      MYSQL_PWD: ${{PREVIEW_DB_ROOT_PASSWORD:?}}
      OTEL_SDK_DISABLED: "true"
      JAVA_TOOL_OPTIONS: "-XX:MaxRAMPercentage=35 -XX:ActiveProcessorCount=2"
    volumes:
      - {json.dumps(str(directory / 'seed-state') + ':/preview-state')}
      - {json.dumps(str(source / 'end_to_end/src/test/resources/application.properties') + ':/var/www/skills/application-e2e.properties:ro')}
      - {json.dumps(str(directory / 'core-seed') + ':/initdb.d:ro')}
    init: true
    tmpfs:
      - /home/gradle/.gradle:size=16m
    restart: unless-stopped
    mem_limit: {memory}
    cpus: {cpus}
    pids_limit: 256
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    labels:
      wud.watch: "false"
    healthcheck:
      # Both applications migrate fresh schemas before Skills can serve HTTP.
      start_period: 600s
      interval: 5s
      timeout: 5s
      retries: 30
'''


def prepare(environ=os.environ):
    source = Path(environ['BRANCHLINE_SOURCE']).resolve()
    directory = Path(environ['BRANCHLINE_PREVIEW_DIR']).resolve()
    artifacts = Path(environ['LABRADOR_ARTIFACTS']).resolve()
    identifier = environ['BRANCHLINE_PREVIEW_ID']
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,80}', identifier):
        raise ValueError('Invalid preview identity')
    port = int(environ['BRANCHLINE_PORT'])
    if not 1024 <= port <= 65535:
        raise ValueError('Invalid preview port')
    manifest = checked_artifacts(artifacts)
    if digest(source / 'build.gradle.kts') not in manifest['skillsBuildContracts']:
        raise ValueError('This branch changes the Java build contract; prepare a matching offline dependency bundle')
    java_image = environ.get('LABRADOR_JAVA_IMAGE', 'gradle:jdk21')
    node_image = environ.get('LABRADOR_NODE_IMAGE', 'node:24-trixie-slim')
    # Pulls are explicit and precede network-disabled compilation.
    run('docker', 'pull', java_image)
    run('docker', 'pull', node_image)
    core = directory / 'build-core'
    skills = directory / 'build-skills'
    for folder in [core, skills, directory / 'mysql', directory / 'seed-state']:
        folder.mkdir(parents=True, exist_ok=True)
    os.chown(directory / 'mysql', 999, 999)
    preview_seed(source, directory)
    core_libraries = compile_app(artifacts / 'core-source', core, artifacts, 'core', manifest, java_image)
    package_app(core, 'nl.tudelft.labracore.LabracoreApplication', core_libraries)
    skills_libraries = compile_app(source, skills, artifacts, 'skills', manifest, java_image)
    frontend(source, skills, node_image)
    package_app(skills, 'nl.tudelft.skills.SkillCircuitsApplication', skills_libraries)

    core_image = 'branchline-labracore:' + identifier
    skills_image = 'branchline-skills:' + identifier
    core_docker = (source / 'docker/labracore/Dockerfile').read_text()
    core_docker = change(core_docker, r'^FROM .*$', 'FROM ' + java_image)
    core_docker = change(core_docker, r'^RUN git clone .*$', 'COPY build/libs/application.jar /var/www/labracore/labracore.jar\nCOPY build/preview-libs /var/www/labracore/lib')
    # Public base images vary in Debian/Ubuntu packaging; default-mysql-client is
    # the Debian package while Ubuntu provides mysql-client.
    core_docker = change(core_docker, r'^RUN apt update && apt install mysql-client -y$', 'RUN apt-get update && (apt-get install -y --no-install-recommends mysql-client curl || apt-get install -y --no-install-recommends default-mysql-client curl)')
    if 'gitlab' in core_docker.lower():
        raise ValueError('Unsupported Docker recipe still references GitLab')
    (core / 'context/Dockerfile').write_text(core_docker)
    shutil.copy2(source / 'docker/labracore/application.yaml', core / 'context/application.yaml')
    run('docker', 'build', '--tag', core_image, str(core / 'context'))

    skills_docker = (source / 'docker/Dockerfile').read_text()
    skills_docker = change(skills_docker, r'^FROM .*$', 'FROM ' + core_image)
    skills_docker = change(skills_docker, r'^COPY build/libs/\*\.jar /var/www/skills/skills.jar$', 'COPY build/libs/application.jar /var/www/skills/skills.jar\nCOPY build/preview-libs /var/www/skills/lib')
    # Compiled frontend assets need no Node runtime. Preserve the original startup
    # and health commands, guarding only the upstream SQL seeding on restart.
    skills_docker = re.sub(r'^RUN curl -fsSL https://deb.nodesource.com/[^\n]+\n\s*&& apt install -y nodejs\n', '', skills_docker, flags=re.M)
    skills_docker = change(skills_docker, r'for sqlfile in /initdb.d/\*; do mysql -h database -u root < "\$sqlfile"; done', 'if [ ! -f /preview-state/core-seeded ]; then for sqlfile in /initdb.d/*; do mysql -h database -u root < "$sqlfile" || exit 1; done; touch /preview-state/core-seeded; fi')
    if 'gitlab' in skills_docker.lower():
        raise ValueError('Unsupported Docker recipe still references GitLab')
    (skills / 'context/Dockerfile').write_text(skills_docker)
    (skills / 'context/docker').mkdir(exist_ok=True)
    # Preserve Core validation. Only Skills has the historical MySQL boolean
    # mismatch; its preview schema remains entirely owned by Liquibase.
    skills_config = change((source / 'docker/application.yaml').read_text(),
                           r'^      ddl-auto: validate$', '      ddl-auto: none')
    (skills / 'context/docker/application.yaml').write_text(skills_config)
    run('docker', 'build', '--tag', skills_image, str(skills / 'context'))

    envfile = directory / 'runtime.env'
    if not envfile.exists():
        descriptor = os.open(envfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            stream.write('PREVIEW_DB_ROOT_PASSWORD=' + secrets.token_hex(24) + '\n')
    (directory / 'compose.override.yaml').write_text(overlay(directory, source, port,
        environ.get('LABRADOR_BIND_IP', '127.0.0.1'), skills_image,
        environ.get('LABRADOR_APP_MEMORY', '2g'), float(environ.get('LABRADOR_APP_CPUS', '2')),
        environ.get('LABRADOR_DATABASE_IMAGE', 'mysql:9.0.1')))
    (directory / 'build-provenance.json').write_text(json.dumps({
        'skillsSha': environ['BRANCHLINE_SHA'], 'coreSha': manifest['coreSha'],
        'artifactsSha256': digest(artifacts / 'manifest.json'), 'recipeSha256': digest(Path(__file__)),
        'composeSha256': digest(source / 'end_to_end/compose.yml'),
        'images': {'skills': skills_image, 'core': core_image},
        'builderImages': {image: subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', image], text=True).strip()
                          for image in [java_image, node_image]},
    }, indent=2) + '\n')


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, stop_builders)
    signal.signal(signal.SIGINT, stop_builders)
    try:
        prepare()
    except subprocess.CalledProcessError as error:
        print(f'Preview build command failed ({error.returncode}): {error.cmd[0]}', file=sys.stderr)
        raise SystemExit(error.returncode)
