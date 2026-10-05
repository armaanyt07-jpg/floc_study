"""
Pull only the files needed for the hydrodynamic/physical-feature model out of
the 2 GB SDR zip, without downloading the whole archive.

Needs:  pip install remotezip
Usage:  python download_data.py <URL-of-NonVectrinoData-zip> [out_dir]
        (copy the URL from the Download link on purl.stanford.edu/wv787xr0534)

If the server doesn't support HTTP range requests, RemoteZip will error out;
in that case download the zip normally and run with a local path instead
(zipfile.ZipFile works the same way).
"""
import os, re, sys
from remotezip import RemoteZip

url = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else "data"

def wanted(name):
    if name.startswith("__MACOSX") or name.endswith("/"):
        return False
    # target: LISST (only exists at P2)
    if "/LISST/" in name:
        return True
    # salinity/temperature: all CTDs are tiny; P2's salinity is unusable,
    # so P1/P3 are the likely salinity sources
    if "/CTD/" in name:
        return True
    # u_b, u_bar, epsilon: ADV at 15 cmab on P2 (same platform as the LISST)
    if re.search(r"/ADV/\w+/P2/adv15_\d+\.mat$", name):
        return True
    return False

def done(info):
    """Already extracted completely? (size match guards against a file
    that was cut off when the previous run was interrupted)"""
    p = os.path.join(out, info.filename)
    return os.path.isfile(p) and os.path.getsize(p) == info.file_size

with RemoteZip(url) as z:
    infos = [i for i in z.infolist() if wanted(i.filename)]
    todo = [i for i in infos if not done(i)]
    total = sum(i.compress_size for i in todo) / 1e6
    print(f"{len(infos)} files matched, {len(infos) - len(todo)} already on disk, "
          f"{len(todo)} to fetch (~{total:.0f} MB compressed)")
    for n, i in enumerate(todo, 1):
        try:
            z.extract(i, out)
        except Exception as e:          # network hiccup: skip, rerun to retry
            print("  failed:", i.filename, e)
        if n % 100 == 0:
            print(f"  {n}/{len(todo)}")
print("done ->", out, "(rerun the same command if anything failed)")