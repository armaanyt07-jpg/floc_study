"""
Fetch only the files the feature pipeline needs from the 2.5 GB
NonVectrinoData.zip archive (Stanford Digital Repository, purl wv787xr0534),
without downloading the whole archive.

Usage:
    python download_data.py                      # default URL, saves to Data/
    python download_data.py <url-or-zip> [out_dir]
    python download_data.py --lisst-only         # only the LISST files (enough for build_psd.py)

The remote archive is read with HTTP range requests. If the server does not
support them, download the zip in a browser and pass its local path instead.
"""
import os
import re
import sys
import zipfile

DEFAULT_URL = "https://stacks.stanford.edu/file/druid:wv787xr0534/NonVectrinoData.zip"

lisst_only = "--lisst-only" in sys.argv
args = [a for a in sys.argv[1:] if a != "--lisst-only"]
src = args[0] if args else DEFAULT_URL
out = args[1] if len(args) > 1 else "Data"


def wanted(name):
    if name.startswith("__MACOSX") or name.endswith("/"):
        return False
    # target: LISST (only at P2)
    if "/LISST/" in name:
        return True
    if lisst_only:
        return False
    # temperature and salinity: all CTDs are small; P2 salinity is unusable,
    # so P1 provides salinity
    if "/CTD/" in name:
        return True
    # waves, currents, turbulence: ADV at 15 cmab on P2 (same platform as the LISST)
    if re.search(r"/ADV/\w+/P2/adv15_\d+\.mat$", name):
        return True
    return False


def done(info):
    """Already extracted completely? (a size match guards against a file
    cut off by an interrupted run)"""
    p = os.path.join(out, info.filename)
    return os.path.isfile(p) and os.path.getsize(p) == info.file_size


def open_archive(path_or_url):
    if os.path.isfile(path_or_url):
        return zipfile.ZipFile(path_or_url)
    from remotezip import RemoteZip
    return RemoteZip(path_or_url)


with open_archive(src) as z:
    infos = [i for i in z.infolist() if wanted(i.filename)]
    todo = [i for i in infos if not done(i)]
    total = sum(i.compress_size for i in todo) / 1e6
    print(f"{len(infos)} files matched, {len(infos) - len(todo)} already on disk, "
          f"{len(todo)} to fetch (~{total:.0f} MB compressed)")
    failed = 0
    for n, i in enumerate(todo, 1):
        try:
            z.extract(i, out)
        except Exception as e:          # network error: skip, rerun to retry
            failed += 1
            print("  failed:", i.filename, e)
        if n % 100 == 0:
            print(f"  {n}/{len(todo)}")
print(f"done -> {out}" + (f" ({failed} failed, rerun the same command to retry)" if failed else ""))
