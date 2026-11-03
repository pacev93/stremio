#!/usr/bin/env python3
"""Check the final IPK's ownership and access modes against the working original.

Usage: python3 tests/package/check.py original.ipk candidate.ipk
Reads the actual distribution archives, not intermediate staging files.
"""
import io
import json
import pathlib
import subprocess
import sys
import tarfile


def read(path, archive):
    blob = subprocess.check_output(['ar', 'p', str(path), archive])
    with tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz') as t:
        return {m.name: (m, t.extractfile(m).read() if m.isfile() else None)
                for m in t.getmembers()}


def main(original, candidate):
    app = 'usr/palm/applications/tv.stremioorigin.app/'
    for archive in ['control.tar.gz', 'data.tar.gz']:
        expected, actual = read(original, archive), read(candidate, archive)
        assert expected.keys() == actual.keys(), 'Package entries changed'
        for name, (m, _) in actual.items():
            ref = expected[name][0]
            assert m.type == ref.type, f'{name}: entry type changed'
            assert m.mode == ref.mode, f'{name}: mode {m.mode:o}, expected {ref.mode:o}'
            assert m.uid == m.gid == 0, f'{name}: unexpected owner'
            if m.isdir():
                assert m.mode & 0o005 == 0o005, f'{name}: not traversable by other users'
        if archive == 'data.tar.gz':
            executable = actual[app + 'stremioorigin'][0]
            assert executable.mode & 0o055 == 0o055, 'App not readable/executable by group and other users'
            changed = sorted(n for n in actual if actual[n][1] != expected[n][1])
            allowed = [app + 'appinfo.json', app + 'stremioorigin',
                       'usr/palm/packages/tv.stremioorigin.app/packageinfo.json']
            assert set(changed) <= set(allowed), f'Unexpected payload changes: {changed}'
            old = json.loads(expected[app + 'appinfo.json'][1])
            new = json.loads(actual[app + 'appinfo.json'][1])
            version = new['version']; new['version'] = old['version']
            assert new == old, 'App metadata changed beyond version'
            print(f'PASS {version}: executable 0755; all {len(actual)} data entry modes match original')
        print(f'PASS {archive}: same entries/types, original permissions, root ownership')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
