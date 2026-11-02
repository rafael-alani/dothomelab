"""Scoped SSH transport. Uses strict host keys and never a root login."""
import hashlib
import json
import subprocess


class Transport:
    def __init__(self, host, key):
        self.command = ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                        '-o', 'ConnectTimeout=8', '-o', 'ServerAliveInterval=15',
                        '-o', 'ServerAliveCountMax=2', '-o', 'IdentitiesOnly=yes',
                        '-i', str(key), 'reference-ingest@' + host]

    def request(self, header, body=b'', file=None):
        process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            process.stdin.write((json.dumps(header) + '\n').encode())
            if file:
                with file.open('rb') as source:
                    while chunk := source.read(1024 * 1024):
                        process.stdin.write(chunk)
            else:
                process.stdin.write(body)
            process.stdin.close()
            process.stdin = None
            output, _ = process.communicate(timeout=900)
            if process.returncode:
                raise RuntimeError('archive_unavailable_or_rejected')
            response = json.loads(output)
            if not response.get('ok'):
                raise RuntimeError('archive_rejected')
            return response['result']
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()

    def put(self, file):
        with file.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        return self.request({'action': 'put', 'sha256': digest,
                             'extension': file.suffix[1:].lower(), 'bytes': file.stat().st_size}, file=file)

    def inventory(self, document):
        body = json.dumps(document, ensure_ascii=False).encode()
        return self.request({'action': 'inventory', 'bytes': len(body)}, body)
