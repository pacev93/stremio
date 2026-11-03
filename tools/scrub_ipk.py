#!/usr/bin/env python3
# scrub_ipk.py <file.ipk>: the archives record who built them (the user and group names, the ids); the package
# carries "root" and 0 instead, so nothing of the build machine travels with it. File bytes are unchanged.
# --reference original.ipk also restores the original entry modes, independent of the staging machine's umask.
import argparse, io, sys, tarfile

def scrub_tar(blob, gz, reference=None):
    src = tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz' if gz else 'r:')
    out = io.BytesIO()
    dst = tarfile.open(fileobj=out, mode='w:gz' if gz else 'w', format=tarfile.GNU_FORMAT)
    for m in src.getmembers():
        m.uid = m.gid = 0; m.uname = m.gname = 'root'
        if reference is not None:
            if m.name not in reference or m.type != reference[m.name][1]:
                raise ValueError('reference entry missing or type differs: ' + m.name)
            m.mode = reference[m.name][0]
        dst.addfile(m, src.extractfile(m) if m.isfile() else None)
    dst.close(); return out.getvalue()

def members(data):
    assert data[:8] == b'!<arch>\n', 'not an ar archive'
    i, result = 8, []
    while i < len(data):
        h = data[i:i + 60]; name = h[:16].decode().strip(); size = int(h[48:58].decode().strip()); body = data[i + 60:i + 60 + size]
        result.append((name, h, body)); i += 60 + size + (size & 1)
    return result

def main(path, reference=None):
    modes = {}
    if reference:
        for name, _, body in members(open(reference, 'rb').read()):
            n = name.rstrip('/')
            if n.endswith('.tar.gz') or n.endswith('.tar'):
                with tarfile.open(fileobj=io.BytesIO(body), mode='r:gz' if n.endswith('.gz') else 'r:') as src:
                    modes[n] = {m.name: (m.mode, m.type) for m in src.getmembers()}
    out = bytearray(b'!<arch>\n')
    for name, h, body in members(open(path, 'rb').read()):
        n = name.rstrip('/')
        if reference and (n.endswith('.tar.gz') or n.endswith('.tar')) and n not in modes:
            raise ValueError('reference archive missing: ' + n)
        if n.endswith('.tar.gz'): body = scrub_tar(body, True, modes.get(n))
        elif n.endswith('.tar'): body = scrub_tar(body, False, modes.get(n))
        hdr = (name.ljust(16) + h[16:28].decode() + '0'.ljust(6) + '0'.ljust(6) + h[40:48].decode() + str(len(body)).ljust(10) + '`\n').encode()
        out += hdr + body + (b'\n' if len(body) & 1 else b'')
    open(path, 'wb').write(out)
    # checked again from the file: every entry of every inner archive now says root
    d = bytes(out); i = 8
    while i < len(d):
        h = d[i:i + 60]; n = h[:16].decode().strip().rstrip('/'); size = int(h[48:58].decode().strip()); body = d[i + 60:i + 60 + size]; i += 60 + size + (size & 1)
        if n.endswith('.tar.gz') or n.endswith('.tar'):
            for m in tarfile.open(fileobj=io.BytesIO(body), mode='r:gz' if n.endswith('.gz') else 'r:').getmembers():
                if m.uname not in ('root', '') or m.gname not in ('root', '') or m.uid or m.gid: sys.exit('scrub failed: ' + m.name)
                if reference and (m.mode, m.type) != modes[n][m.name]: sys.exit('reference mode differs: ' + m.name)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrub archive ownership; optionally restore exact modes from an upstream IPK.')
    parser.add_argument('path')
    parser.add_argument('--reference', help='Known-good original IPK with the same entry names and types')
    args = parser.parse_args()
    main(args.path, args.reference)
