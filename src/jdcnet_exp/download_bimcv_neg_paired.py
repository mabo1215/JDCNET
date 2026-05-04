"""Download same-patient CT+CXR paired subjects from BIMCV-COVID19- (negative cohort).

Source: BSC B2Drop public share
  https://b2drop.bsc.es/index.php/s/BIMCV-COVID19

The dataset is distributed as multiple .tar.gz archives, each with a companion
.tar-tvf.txt file listing the archive contents (output of ``tar -tvf``).

Download strategy
-----------------
1. WebDAV PROPFIND the share root to enumerate all .tar-tvf.txt manifest files.
2. Download each manifest (lightweight, plain text) and parse it to build a map
   {subject_id: {archive_name: {"ct": [...], "cxr": [...]}}} without touching
   the large .tar.gz files yet.
3. Identify archives that contain at least one subject with both CT (.nii.gz)
   and CXR (bp-chest *.png) files.
4. Download only those .tar.gz archives, extract the paired files, and organise
   them into output_dir/sub-SUBJECTID/{ct,cxr}/.
5. Write a JSON report and delete the downloaded archives.

Dry-run mode (--dry-run) stops after step 3 and reports estimated paired counts.

Usage
-----
  # Dry run — enumerate paired subjects without downloading:
  python -m jdcnet_exp.download_bimcv_neg_paired --dry-run --output-dir /data/bimcv_neg_paired

  # Full download (all archives):
  python -m jdcnet_exp.download_bimcv_neg_paired --output-dir /data/bimcv_neg_paired

  # Limit to specific archives (e.g. for partial/incremental download):
  python -m jdcnet_exp.download_bimcv_neg_paired \\
      --archives covid19_neg_posi_part01.tar.gz covid19_neg_posi_part02.tar.gz \\
      --output-dir /data/bimcv_neg_paired

B2Drop share token is read from --share-token (default: BIMCV-COVID19-cIter_1_2-Negative).
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import tarfile
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

import requests
import time


ROOT = Path(__file__).resolve().parents[2]

# --------------------------------------------------------------------------- #
# B2Drop / NextCloud constants
# --------------------------------------------------------------------------- #
BIMCV_NEG_SHARE_TOKEN = "BIMCV-COVID19-cIter_1_2-Negative"
_WEBDAV_BASE = "https://b2drop.bsc.es/public.php/webdav"
_DOWNLOAD_BASE = "https://b2drop.bsc.es/index.php/s/{token}/download"

# --------------------------------------------------------------------------- #
# File-type helpers (same naming conventions as BIMCV-COVID19+)
# --------------------------------------------------------------------------- #
# BIMCV-COVID19+ uses sub-S\d+ format; older iter1 may use sub-S\d+ too.
# Keep the S-prefix form for now to stay consistent with prepare_bimcv_neg_dataset.py.
_SUBJECT_RE = re.compile(r"sub-(S\d+)")
_CT_SUFFIX = (".nii", ".nii.gz")
_CXR_SUFFIX = ("_cr.png", "_dx.png", "_rx.png")


def _is_ct(name: str) -> bool:
    return any(name.endswith(s) for s in _CT_SUFFIX)


def _is_cxr(name: str) -> bool:
    return "bp-chest" in name and any(name.endswith(s) for s in _CXR_SUFFIX)


# --------------------------------------------------------------------------- #
# B2Drop WebDAV helpers
# --------------------------------------------------------------------------- #

def _webdav_auth(token: str) -> str:
    """Return the Basic auth header value for a NextCloud public share."""
    return "Basic " + base64.b64encode(f"{token}:".encode()).decode()


def _webdav_list(token: str, path: str = "/") -> list[dict]:
    """
    PROPFIND the NextCloud WebDAV endpoint and return a list of
    {href, name, size, is_dir} dicts for direct children of *path*.
    """
    url = _WEBDAV_BASE.rstrip("/") + "/" + path.lstrip("/")
    headers = {
        "Authorization": _webdav_auth(token),
        "Depth": "1",
        "Content-Type": "application/xml",
    }
    body = (
        '<?xml version="1.0"?>'
        '<d:propfind xmlns:d="DAV:">'
        "<d:prop><d:resourcetype/><d:getcontentlength/><d:displayname/></d:prop>"
        "</d:propfind>"
    )
    resp = requests.request("PROPFIND", url, headers=headers, data=body, timeout=30)
    resp.raise_for_status()

    ns = {"d": "DAV:"}
    root_el = ET.fromstring(resp.text)
    entries: list[dict] = []
    for response_el in root_el.findall("d:response", ns):
        href = response_el.findtext("d:href", default="", namespaces=ns)
        is_dir = response_el.find(".//d:collection", ns) is not None
        size_el = response_el.find(".//d:getcontentlength", ns)
        size = int(size_el.text) if size_el is not None and size_el.text else 0
        name = href.rstrip("/").split("/")[-1]
        if name:
            entries.append({"href": href, "name": name, "size": size, "is_dir": is_dir})
    # Remove the self-entry (same path as requested)
    entries = [e for e in entries if e["name"] != path.rstrip("/").split("/")[-1] or e["is_dir"]]
    return entries


def _http_download(token: str, filename: str, dest: Path, path: str = "/") -> None:
    """Stream-download a single file from the B2Drop public share.

    Uses WebDAV GET which returns the raw file (no zip wrapping).
    """
    url = _WEBDAV_BASE.rstrip("/") + "/" + filename.lstrip("/")
    headers = {"Authorization": _webdav_auth(token)}
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, headers=headers, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(chunk_size=65536):
                fh.write(chunk)


# --------------------------------------------------------------------------- #
# Manifest / archive helpers
# --------------------------------------------------------------------------- #

def _parse_tvf_manifest(
    text: str,
) -> dict[str, dict[str, list[tuple[str, int]]]]:
    """
    Parse a ``tar -tvf`` listing and return
    {subject_id: {"ct": [(member_path, size), ...], "cxr": [...]}}
    """
    subjects: dict[str, dict[str, list[tuple[str, int]]]] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
        # typical format: permissions owner size date time path
        # '-rw-r--r-- root/root 12345678 2021-01-01 00:00:00 sub-S00001/...'
        try:
            size = int(parts[2])
            member_path = parts[-1]
        except (ValueError, IndexError):
            continue
        m = _SUBJECT_RE.search(member_path)
        if m is None:
            continue
        subject_id = m.group(1)
        entry = subjects.setdefault(subject_id, {"ct": [], "cxr": []})
        basename = member_path.split("/")[-1]
        if _is_ct(basename):
            entry["ct"].append((member_path, size))
        elif _is_cxr(basename):
            entry["cxr"].append((member_path, size))
    return subjects


def _paired_from_subjects(
    subjects: dict[str, dict[str, list[tuple[str, int]]]],
    min_ct_bytes: int,
) -> dict[str, dict]:
    """Return only subjects that have at least one CT and one CXR."""
    paired: dict[str, dict] = {}
    for sid, modalities in subjects.items():
        cts = [c for c in modalities["ct"] if c[1] >= min_ct_bytes]
        cxrs = modalities["cxr"]
        if cts and cxrs:
            best_ct = max(cts, key=lambda x: x[1])
            paired[sid] = {"ct": best_ct, "cxrs": cxrs}
    return paired


def _extract_paired_from_archive(
    archive_path: Path,
    paired_members: dict[str, dict],  # sid -> {ct: (path,size), cxrs: [...]}
    output_dir: Path,
) -> list[str]:
    """Extract only the paired subject files from a local .tar.gz archive."""
    wanted: set[str] = set()
    for info in paired_members.values():
        wanted.add(info["ct"][0])
        wanted.update(c[0] for c in info["cxrs"])

    extracted_sids: list[str] = []
    with tarfile.open(archive_path, "r:gz") as tf:
        for member in tf.getmembers():
            if member.name not in wanted:
                continue
            m = _SUBJECT_RE.search(member.name)
            if m is None:
                continue
            sid = m.group(1)
            basename = member.name.split("/")[-1]
            if _is_ct(basename):
                dest_dir = output_dir / f"sub-{sid}" / "ct"
            else:
                dest_dir = output_dir / f"sub-{sid}" / "cxr"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / basename
            if dest.exists():
                print(f"    SKIP (exists): {dest}")
                if sid not in extracted_sids:
                    extracted_sids.append(sid)
                continue
            member.name = basename  # strip path prefix for extraction
            try:
                tf.extract(member, dest_dir)
                if sid not in extracted_sids:
                    extracted_sids.append(sid)
            except Exception as exc:
                print(f"    ERROR extracting {member.name}: {exc}")
    return extracted_sids



# --------------------------------------------------------------------------- #
# Core pipeline functions
# --------------------------------------------------------------------------- #

# Archive name prefixes that are metadata/derivative, not per-subject data.
_NON_SUBJECT_PREFIXES = ("covid19_neg_derivative", "covid19_neg_metadata", "covid19_neg_sessions")


def _enumerate_archives(token: str) -> list[str]:
    """
    List all subject .tar.gz archives in the B2Drop share root.
    Skips derivative/metadata/sessions archives.
    Falls back to an empty list and prints a warning on error.
    """
    try:
        entries = _webdav_list(token, "/")
    except Exception as exc:
        print(f"WARN: WebDAV listing failed: {exc}")
        return []
    archives = sorted(
        e["name"] for e in entries
        if not e["is_dir"]
        and e["name"].endswith(".tar.gz")
        and not any(e["name"].startswith(p) for p in _NON_SUBJECT_PREFIXES)
    )
    return archives


def _enumerate_manifests(token: str) -> list[str]:
    """Return all .tar-tvf.txt manifest filenames in the share root."""
    try:
        entries = _webdav_list(token, "/")
    except Exception as exc:
        print(f"WARN: WebDAV listing failed: {exc}")
        return []
    return sorted(
        e["name"] for e in entries
        if not e["is_dir"] and e["name"].endswith(".tar-tvf.txt")
    )


def _fetch_manifest_text(token: str, manifest_name: str) -> str:
    """Download a .tar-tvf.txt manifest and return its text content.

    Uses WebDAV direct GET so the file is returned as plain text
    (the index.php/s/.../download endpoint wraps files in a zip).
    Retries once on 429 after a short back-off.
    """
    url = _WEBDAV_BASE.rstrip("/") + "/" + manifest_name.lstrip("/")
    headers = {"Authorization": _webdav_auth(token)}
    for attempt in range(3):
        resp = requests.get(url, headers=headers, timeout=60)
        if resp.status_code == 429:
            wait = 5 * (attempt + 1)
            print(f"    WARN: rate-limited (429), retrying in {wait}s ...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.text
    resp.raise_for_status()  # final raise after all retries exhausted
    return resp.text  # unreachable, satisfies mypy


def run(
    token: str,
    archives: list[str],
    output_dir: Path,
    dry_run: bool,
    min_ct_bytes: int,
) -> dict:
    """
    Main pipeline:
      - If *archives* is empty, auto-discover via WebDAV.
      - Download .tar-tvf.txt manifests for each archive.
      - Identify archives that contain paired subjects.
      - (Unless dry_run) Download and extract those archives.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "share_token": token,
        "archives_scanned": [],
        "archives_with_paired": [],
        "total_paired_subjects": 0,
        "downloaded_subjects": [],
        "dry_run": dry_run,
    }

    # ------------------------------------------------------------------ #
    # Step 1 — discover available archives
    # ------------------------------------------------------------------ #
    if not archives:
        print("Discovering archives via WebDAV ...")
        archives = _enumerate_archives(token)
        if not archives:
            # Fall back: try listing .tar-tvf.txt manifests (same base names)
            manifests = _enumerate_manifests(token)
            archives = [m.replace(".tar-tvf.txt", ".tar.gz") for m in manifests]
        if not archives:
            print("ERROR: Could not enumerate archives from the share. "
                  "Use --archives to specify them explicitly.")
            return report
        print(f"  Found {len(archives)} archive(s).")
    else:
        print(f"Using {len(archives)} user-specified archive(s).")

    report["archives_scanned"] = archives

    # ------------------------------------------------------------------ #
    # Step 2 — fetch manifests and identify paired subjects per archive
    # ------------------------------------------------------------------ #
    # archive_name -> {sid: {ct: (path, size), cxrs: [...]}}
    archive_paired: dict[str, dict[str, dict]] = {}

    for archive_name in archives:
        # Negative arm uses double extension: archive.tar.gz.tar-tvf.txt
        manifest_name = archive_name + ".tar-tvf.txt"
        print(f"\n  Fetching manifest: {manifest_name} ...")
        time.sleep(1)
        try:
            text = _fetch_manifest_text(token, manifest_name)
        except Exception as exc:
            print(f"    WARN: could not fetch manifest {manifest_name}: {exc}")
            print(f"    Skipping {archive_name}.")
            continue

        subjects = _parse_tvf_manifest(text)
        paired = _paired_from_subjects(subjects, min_ct_bytes)
        print(
            f"    {len(subjects)} subjects in manifest, "
            f"{len(paired)} have paired CT+CXR (min_ct_bytes={min_ct_bytes})"
        )
        if paired:
            archive_paired[archive_name] = paired

    paired_with_archive = report["archives_with_paired"] = list(archive_paired.keys())
    # Unique subjects across all archives (a subject may appear in multiple)
    all_sids: set[str] = set()
    for paired in archive_paired.values():
        all_sids.update(paired.keys())
    report["total_paired_subjects"] = len(all_sids)

    print(
        f"\nTotal: {len(paired_with_archive)} archive(s) contain paired subjects; "
        f"{len(all_sids)} unique subjects."
    )

    if dry_run:
        print("DRY RUN — skipping download.")
        return report

    if not paired_with_archive:
        print("No paired subjects found — nothing to download.")
        return report

    # ------------------------------------------------------------------ #
    # Step 3 — download archives and extract paired subjects
    # ------------------------------------------------------------------ #
    already_done: set[str] = set()

    for archive_name in paired_with_archive:
        paired = archive_paired[archive_name]
        # Skip subjects already extracted in an earlier archive
        new_sids = {sid for sid in paired if sid not in already_done}
        if not new_sids:
            print(f"\nSkipping {archive_name} (all paired subjects already extracted).")
            continue

        print(f"\nDownloading {archive_name} ({len(new_sids)} new paired subjects) ...")
        # Use output_dir's filesystem for temp storage to avoid filling the system disk.
        output_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output_dir) as tmp:
            tmp_path = Path(tmp) / archive_name
            try:
                _http_download(token, archive_name, tmp_path)
                print(f"  Download complete ({tmp_path.stat().st_size:,} bytes). Extracting ...")
                relevant_paired = {sid: paired[sid] for sid in new_sids}
                extracted = _extract_paired_from_archive(tmp_path, relevant_paired, output_dir)
                print(f"  Extracted {len(extracted)} subjects.")
                report["downloaded_subjects"].extend(extracted)
                already_done.update(extracted)
            except Exception as exc:
                print(f"  ERROR processing {archive_name}: {exc}")

    print(
        f"\nDone. {len(report['downloaded_subjects'])} subjects in {output_dir}"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download same-patient CT+CXR paired subjects from BIMCV-COVID19- "
            "(negative cohort) via BSC B2Drop."
        )
    )
    parser.add_argument(
        "--output-dir",
        default="/data/bimcv_neg_paired",
        help="Root directory for extracted subjects (sub-S*/ct/ and sub-S*/cxr/).",
    )
    parser.add_argument(
        "--share-token",
        default=BIMCV_NEG_SHARE_TOKEN,
        help="B2Drop share token (default: BIMCV-COVID19).",
    )
    parser.add_argument(
        "--archives",
        nargs="+",
        default=[],
        help=(
            "Explicit list of .tar.gz archive names to process. "
            "If omitted, all archives in the share are auto-discovered via WebDAV."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Enumerate paired subjects from manifests without downloading archives.",
    )
    parser.add_argument(
        "--min-ct-bytes",
        type=int,
        default=1_000_000,
        help="Minimum CT file size in bytes (default: 1 MB) to skip placeholder entries.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    report = run(
        token=args.share_token,
        archives=args.archives,
        output_dir=output_dir,
        dry_run=args.dry_run,
        min_ct_bytes=args.min_ct_bytes,
    )

    report_path = output_dir / "download_report_neg.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()

