# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/chess-review-open/scripts'))
from bundled_engine import platform_key, unpack_engine, resolve_engine


class BundledEngineTests(unittest.TestCase):
    def test_platforms(self):
        for system, arch, expected in [('Darwin','arm64','macos-universal'),('Darwin','x86_64','macos-universal'),('Windows','AMD64','windows-x86_64'),('Windows','ARM64','windows-arm64'),('Linux','aarch64','linux-arm64'),('Linux','x86_64','linux-x86_64')]:
            self.assertEqual(platform_key(system,arch),expected)
        with self.assertRaises(ValueError):
            platform_key('Linux','riscv64')

    def fixture(self, folder, zipped=False):
        vendor=folder/'vendor';vendor.mkdir()
        content=b'example executable contents\n'
        name='engine.zip' if zipped else 'engine.tar.gz'
        key='windows-x86_64' if zipped else 'macos-universal'
        if zipped:
            with zipfile.ZipFile(vendor/name,'w') as pack:
                pack.writestr('stockfish/bin',content)
                pack.writestr('../must-not-extract',b'ignore')
        else:
            with tarfile.open(vendor/name,'w:gz') as pack:
                info=tarfile.TarInfo('stockfish/bin');info.size=len(content);pack.addfile(info,io.BytesIO(content))
                info=tarfile.TarInfo('../must-not-extract');info.size=6;pack.addfile(info,io.BytesIO(b'ignore'))
        spec={'archive':name,'archive_sha256':hashlib.sha256((vendor/name).read_bytes()).hexdigest(),'member':'stockfish/bin','binary_sha256':hashlib.sha256(content).hexdigest()}
        (vendor/'manifest.json').write_text(json.dumps({'platforms':{key:spec}}))
        return vendor,key,content

    def test_archive_cache_and_repair(self):
        for zipped in [False,True]:
            with tempfile.TemporaryDirectory() as temp:
                folder=Path(temp);vendor,key,content=self.fixture(folder,zipped)
                engine=unpack_engine(key,folder/'cache',vendor)
                self.assertEqual(engine.read_bytes(),content)
                stamp=engine.stat().st_mtime_ns
                self.assertEqual(unpack_engine(key,folder/'cache',vendor),engine)
                self.assertEqual(engine.stat().st_mtime_ns,stamp)
                engine.write_bytes(b'corrupt cache')
                self.assertEqual(unpack_engine(key,folder/'cache',vendor).read_bytes(),content)
                self.assertFalse(list(folder.rglob('must-not-extract')))

    def test_rejects_corrupt_archive_even_with_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);vendor,key,_=self.fixture(folder)
            unpack_engine(key,folder/'cache',vendor)
            (vendor/'engine.tar.gz').write_bytes(b'corrupt archive')
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):
                unpack_engine(key,folder/'cache',vendor)

    def test_explicit_override_does_not_require_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            engine=Path(temp)/'chosen-engine';engine.write_text('custom engine')
            self.assertEqual(resolve_engine(str(engine)),str(engine.resolve()))


if __name__=='__main__':
    unittest.main()
