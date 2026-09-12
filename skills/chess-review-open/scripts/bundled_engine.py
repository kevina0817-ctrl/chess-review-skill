#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Select and unpack the bundled Stockfish. No network access or downloads."""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

VENDOR = Path(__file__).resolve().parent.parent / 'vendor' / 'stockfish'


def platform_key(system=None, machine=None):
    system = (system or platform.system()).lower()
    machine = (machine or platform.machine()).lower()
    arch = {'amd64': 'x86_64', 'x64': 'x86_64', 'aarch64': 'arm64'}.get(machine, machine)
    if system == 'darwin' and arch in ('arm64', 'x86_64'):
        return 'macos-universal'
    if system in ('linux', 'windows') and arch in ('arm64', 'x86_64'):
        return system + '-' + arch
    raise ValueError(f'No bundled Stockfish for {system}/{machine}. Supply --engine for this platform.')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def unpack_engine(key, cache_dir, vendor=VENDOR):
    vendor = Path(vendor)
    manifest = json.loads((vendor / 'manifest.json').read_text(encoding='utf-8'))
    spec = manifest['platforms'][key]
    archive_name = spec['archive']
    if Path(archive_name).name != archive_name:
        raise ValueError('Archive must be a filename inside the vendor directory.')
    archive = vendor / archive_name
    if not archive.is_file():
        raise FileNotFoundError(f'Bundled archive missing: {archive_name}. Install the complete skill folder, including vendor/.')
    # Verify the original official asset even when a cached executable exists.
    if sha256(archive) != spec['archive_sha256']:
        raise ValueError(f'Bundled archive checksum mismatch: {archive_name}')
    folder = Path(cache_dir).resolve() / ('stockfish-' + spec['binary_sha256'][:16])
    binary = folder / ('stockfish.exe' if key.startswith('windows-') else 'stockfish')
    if binary.is_file() and sha256(binary) == spec['binary_sha256']:
        if os.name != 'nt':
            binary.chmod(0o700)
        return binary
    folder.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix='.stockfish-', dir=folder)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, 'wb') as dest:
            if archive_name.endswith('.zip'):
                with zipfile.ZipFile(archive) as pack:
                    with pack.open(spec['member']) as src:
                        shutil.copyfileobj(src, dest)
            else:
                with tarfile.open(archive, 'r:gz') as pack:
                    member = pack.getmember(spec['member'])
                    if not member.isfile():
                        raise ValueError('Expected a regular executable in the archive.')
                    with pack.extractfile(member) as src:
                        shutil.copyfileobj(src, dest)
        if sha256(temporary) != spec['binary_sha256']:
            raise ValueError('Unpacked executable checksum mismatch.')
        if os.name != 'nt':
            temporary.chmod(0o700)
        temporary.replace(binary)
    finally:
        temporary.unlink(missing_ok=True)
    return binary


def resolve_engine(explicit=None, cache_dir='work/engine-cache'):
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file():
            return str(path.resolve())
        resolved = shutil.which(explicit)
        if resolved:
            return resolved
        raise FileNotFoundError(f'Explicit engine not found: {explicit}')
    return str(unpack_engine(platform_key(), cache_dir))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir', default='work/engine-cache')
    parser.add_argument('--verify', action='store_true', help='Start the local engine and verify its UCI response')
    args = parser.parse_args()
    engine = resolve_engine(cache_dir=args.cache_dir)
    result = {'platform': platform_key(), 'engine': engine, 'network_required': False}
    if args.verify:
        process = subprocess.run([engine], input='uci\nquit\n', capture_output=True, text=True, timeout=30)
        if process.returncode != 0 or 'uciok' not in process.stdout:
            raise RuntimeError('Bundled engine did not complete the UCI handshake.')
        result['name'] = next(line[8:] for line in process.stdout.splitlines() if line.startswith('id name '))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
