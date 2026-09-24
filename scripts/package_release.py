#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Package the generic plugin and documentation, never local review archives."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '__pycache__', '.venv', 'node_modules', 'work', 'chess-reviews', 'engine-cache'}


def release_files():
    for name in ('README.md', 'LICENSE', '.gitignore', 'docs', 'plugins', 'scripts', 'tests'):
        source = ROOT / name
        candidates = sorted(source.rglob('*')) if source.is_dir() else [source]
        for item in candidates:
            rel = item.relative_to(ROOT)
            if any(part in SKIP for part in rel.parts):
                continue
            if item.is_symlink():
                raise ValueError(f'Release must not contain symlinks: {rel}')
            if not item.is_file() or item.suffix in ('.pyc', '.pyo') or item.name == '.DS_Store':
                continue
            if item.name.startswith(('.chess-review-', '.env')):
                raise ValueError(f'Local configuration must not be shipped: {rel}')
            yield item, rel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'plugins/chess-review/.codex-plugin/plugin.json').read_text())
    version = manifest['version']
    if not re.fullmatch(r'[a-zA-Z0-9.-]+', version):
        raise ValueError('Invalid release version')
    prefix = f'chess-review-{version}'
    args.out.mkdir(parents=True, exist_ok=True)
    output = args.out / f'{prefix}.zip'
    files = list(release_files())
    with zipfile.ZipFile(output, 'w') as archive:
        for source, relative in files:
            # Engine packages and screenshots are already compressed.
            method = zipfile.ZIP_STORED if source.suffix in ('.zip', '.gz', '.png') else zipfile.ZIP_DEFLATED
            archive.write(source, f'{prefix}/{relative.as_posix()}', compress_type=method)
    with zipfile.ZipFile(output) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f'Corrupt archive member: {bad}')
    digest = hashlib.sha256()
    with output.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    checksum = digest.hexdigest()
    (args.out / 'SHA256SUMS').write_text(f'{checksum}  {output.name}\n')
    info = {'version': version, 'archive': output.name, 'bytes': output.stat().st_size,
            'sha256': checksum, 'files': [str(relative) for _, relative in files]}
    (args.out / f'{prefix}.manifest.json').write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'archive': str(output.resolve()), 'files': len(files),
                      'bytes': info['bytes'], 'sha256': checksum}))


if __name__ == '__main__':
    main()
