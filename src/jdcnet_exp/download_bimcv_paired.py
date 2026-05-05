"""Download same-patient CT+CXR paired subjects from BIMCV-COVID19+ via B2Drop.

Source: BSC B2Drop public share
  https://b2drop.bsc.es/index.php/s/BIMCV-COVID19

This downloader mirrors the BIMCV-negative pipeline but targets the positive
cohort share token and writes a dedicated positive report.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import tarfile
import tempfile
import time
from pathlib import Path
from xml.etree import ElementTree as ET

import requests


ROOT = Path(__file__).resolve().parents[2]

BIMCV_POS_SHARE_TOKEN = "BIMCV-COVID19"
_WEBDAV_BASE = "https://b2drop.bsc.es/public.php/webdav"
_SUBJECT_RE = re.compile(r"sub-(S\d+)")
_CT_SUFFIX = (".nii", ".nii.gz")
_CXR_SUFFIX = ("_cr.png", "_dx.png", "_rx.png")


def _is_ct(name: str) -> bool:
    return any(name.endswith(s) for s in _CT_SUFFIX)


def _is_cxr(name: str) -> bool:
    return "bp-chest" in name and any(name.endswith(s) for s in _CXR_SUFFIX)


def _webdav_auth(token: str) -> str:
    return "Basic " + base64.b64encode(f"{token}:".encode()).decode()


def _webdav_list(token: str, path: str = "/") -> list[dict]:
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
    entries = [e for e in entries if e["name"] != path.rstrip("/").split("/")[-1] or e["is_dir"]]
    return entries


def _http_download(token: str, filename: str, dest: Path) -> None:
    url = _WEBDAV_BASE.rstrip("/") + "/" + filename.lstrip("/")
    headers = {"Authorization": _webdav_auth(token)}
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, headers=headers, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(chunk_size=65536):
                fh.write(chunk)


def _parse_tvf_manifest(text: str) -> dict[str, dict[str, list[tuple[str, int]]]]:
    subjects: dict[str, dict[str, list[tuple[str, int]]]] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
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


def _paired_from_subjects(subjects: dict[str, dict[str, list[tuple[str, int]]]], min_ct_bytes: int) -> dict[str, dict]:
    paired: dict[str, dict] = {}
    for sid, modalities in subjects.items():
        cts = [c for c in modalities["ct"] if c[1] >= min_ct_bytes]
        cxrs = modalities["cxr"]
        if cts and cxrs:
            best_ct = max(cts, key=lambda x: x[1])
            paired[sid] = {"ct": best_ct, "cxrs": cxrs}
    return paired


def _extract_paired_from_archive(archive_path: Path, paired_members: dict[str, dict], output_dir: Path) -> list[str]:
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
            dest_dir = output_dir / f"sub-{sid}" / ("ct" if _is_ct(basename) else "cxr")
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / basename
            if dest.exists():
                if sid not in extracted_sids:
                    extracted_sids.append(sid)
                continue
            member.name = basename
            tf.extract(member, dest_dir)
            if sid not in extracted_sids:
                extracted_sids.append(sid)
    return extracted_sids


def _enumerate_archives(token: str) -> list[str]:
    entries = _webdav_list(token, "/")
    return sorted(e["name"] for e in entries if (not e["is_dir"]) and (e["name"].endswith(".tar.gz") or e["name"].endswith(".tgz")))


def _manifest_name_candidates(archive_name: str) -> list[str]:
    candidates = [archive_name + ".tar-tvf.txt"]
    if archive_name.endswith(".tgz"):
        candidates.append(archive_name[:-4] + ".tar-tvf.txt")
    elif archive_name.endswith(".tar.gz"):
        candidates.append(archive_name[:-7] + ".tar-tvf.txt")
    return list(dict.fromkeys(candidates))


def _fetch_manifest_text(token: str, archive_name: str) -> tuple[str, str]:
    headers = {"Authorization": _webdav_auth(token)}
    last_error: str | None = None
    for manifest_name in _manifest_name_candidates(archive_name):
        url = _WEBDAV_BASE.rstrip("/") + "/" + manifest_name.lstrip("/")
        for attempt in range(3):
            resp = requests.get(url, headers=headers, timeout=60)
            if resp.status_code == 404:
                last_error = f"404 for {manifest_name}"
                break
            if resp.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"    WARN: rate-limited (429), retrying in {wait}s ...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return manifest_name, resp.text
    raise FileNotFoundError(last_error or f"manifest not found for {archive_name}")


def run(token: str, archives: list[str], output_dir: Path, dry_run: bool, min_ct_bytes: int) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "share_token": token,
        "archives_scanned": [],
        "archives_with_paired": [],
        "total_paired_subjects": 0,
        "downloaded_subjects": [],
        "dry_run": dry_run,
    }

    if not archives:
        print("Discovering archives via WebDAV ...")
        archives = _enumerate_archives(token)
        if not archives:
            print("ERROR: Could not enumerate archives from the share.")
            return report
        print(f"  Found {len(archives)} archive(s).")
    report["archives_scanned"] = archives

    archive_paired: dict[str, dict[str, dict]] = {}
    for archive_name in archives:
        print(f"\n  Fetching manifest for: {archive_name} ...")
        time.sleep(1)
        try:
            manifest_name, text = _fetch_manifest_text(token, archive_name)
            print(f"    using {manifest_name}")
        except Exception as exc:
            print(f"    WARN: could not fetch manifest for {archive_name}: {exc}")
            continue
        subjects = _parse_tvf_manifest(text)
        paired = _paired_from_subjects(subjects, min_ct_bytes)
        print(f"    {len(subjects)} subjects in manifest, {len(paired)} have paired CT+CXR (min_ct_bytes={min_ct_bytes})")
        if paired:
            archive_paired[archive_name] = paired

    report["archives_with_paired"] = list(archive_paired.keys())
    all_sids: set[str] = set()
    for paired in archive_paired.values():
        all_sids.update(paired.keys())
    report["total_paired_subjects"] = len(all_sids)
    print(f"\nTotal: {len(report['archives_with_paired'])} archive(s) contain paired subjects; {len(all_sids)} unique subjects.")

    if dry_run:
        print("DRY RUN - skipping download.")
        return report

    already_done: set[str] = set()
    for archive_name in report["archives_with_paired"]:
        paired = archive_paired[archive_name]
        new_sids = {sid for sid in paired if sid not in already_done}
        if not new_sids:
            continue
        print(f"\nDownloading {archive_name} ({len(new_sids)} new paired subjects) ...")
        with tempfile.TemporaryDirectory(dir=output_dir) as tmp:
            tmp_path = Path(tmp) / archive_name
            try:
                _http_download(token, archive_name, tmp_path)
                relevant = {sid: paired[sid] for sid in new_sids}
                extracted = _extract_paired_from_archive(tmp_path, relevant, output_dir)
                report["downloaded_subjects"].extend(extracted)
                already_done.update(extracted)
                print(f"  Extracted {len(extracted)} subjects.")
            except Exception as exc:
                print(f"  ERROR processing {archive_name}: {exc}")

    print(f"\nDone. {len(report['downloaded_subjects'])} subjects in {output_dir}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download same-patient CT+CXR paired subjects from BIMCV-COVID19+ via B2Drop."
    )
    parser.add_argument("--output-dir", default="/data/bimcv_paired", help="Root directory for extracted subjects.")
    parser.add_argument("--share-token", default=BIMCV_POS_SHARE_TOKEN, help="B2Drop share token for positive cohort.")
    parser.add_argument("--archives", nargs="+", default=[], help="Explicit list of archive names to process.")
    parser.add_argument("--dry-run", action="store_true", help="Enumerate paired subjects without downloading archives.")
    parser.add_argument("--min-ct-bytes", type=int, default=1_000_000, help="Minimum CT file size in bytes.")
    args = parser.parse_args()

    report = run(
        token=args.share_token,
        archives=args.archives,
        output_dir=Path(args.output_dir),
        dry_run=args.dry_run,
        min_ct_bytes=args.min_ct_bytes,
    )
    report_path = Path(args.output_dir) / "download_report_pos.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
