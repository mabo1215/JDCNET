"""Pseudonymized inventory of a hospital scoliosis imaging export.

The raw export is organised as

    <exam date YYYYMMDD>/<NAME>_<hospital id>_<HHMMSS>/<series description>_<HHMMSS>_<series number>/<instance>.jpg

so its folder names carry direct identifiers. This module assigns stable
pseudonymous identifiers to patients, studies and series, and writes

* a private linkage key, stored next to the raw data and outside version
  control, that maps every pseudonymous identifier back to the hospital
  identifier and the raw relative path; and
* de-identified manifests (patients, studies, series, radiograph images) that
  contain no names, hospital identifiers, exact dates or acquisition times.

Identifiers are stable across reruns: existing assignments are read from the
linkage key, and only new patients, studies or series receive new numbers.
Downstream code should address images through ``series_dir`` instead of the
raw folder names.

The raw export location is local configuration: set ``SCOLIOSIS_RAW_ROOT`` or
write its repository-relative path to ``data/scoliosis_private/raw_root.txt``.

Usage (from ``src/``)::

    python -m scoliosis_exp.manifest
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_DIR = REPO_ROOT / "data" / "scoliosis_private"
RAW_ROOT_ENV = "SCOLIOSIS_RAW_ROOT"
RAW_ROOT_POINTER = PRIVATE_DIR / "raw_root.txt"
DEFAULT_KEY_PATH = PRIVATE_DIR / "linkage_key.csv"
DEFAULT_OUT_DIR = REPO_ROOT / "src" / "results" / "scoliosis_manifest"
SITE_CODE = "SC"

STUDY_DIR_RE = re.compile(r"^(?P<name>.+)_(?P<hid>\d+)_(?P<time>\d{6})$")
SERIES_DIR_RE = re.compile(r"^(?P<desc>.+)_(?P<time>\d{6}|HHMMSS)_(?P<num>\d+)$")
INSTANCE_RE = re.compile(r"^(?P<idx>\d+)(?:_(?P<copy>\d+))?\.jpe?g$", re.IGNORECASE)

KEY_FIELDS = ["level", "pseudo_id", "parent_id", "hospital_id", "patient_name", "exam_date", "raw_relpath"]

# Keyword rules applied to the upper-cased series description. MR is tested
# first because no MR description in this export contains a DR keyword.
MR_KEYWORDS = (
    "T1W", "T2W", "STIR", "SURVEY", "FLAIR", "DWI", "LOC", "OSAG", "OAX", "AX T2",
    "COR T1", "SAG T1", "LAVA", "PD_TSE", "SCREEN SAVE", "FLEX", "PROPELLER", "CUBE", "FSE",
)
DR_KEYWORDS = ("SPINE", "CHEST", "PELVIS")
DR_EXACT = ("AP", "LATERAL")

# Burned-in identifier status from a visual review on 2026-11-01:
#   confirmed    - patient name / hospital id / dates / study id rendered in pixels
#   not_observed - one image of every series in this role was inspected
#   spot_checked - a sample of series in this role was inspected
# Series flagged ``confirmed`` must never be used for training or figures.
PHI_BY_ROLE = {
    "ct_rendered_film_aw": "confirmed",
    "ct_dose_report": "confirmed",
    "ct_rendered_film_display": "spot_checked",
    "ct_scout": "not_observed",
    "ct_axial": "spot_checked",
    "dr_whole_spine": "not_observed",
    "dr_regional": "not_observed",
    "mr_screen_save": "not_observed",
    "mr_localizer": "spot_checked",
    "mr_sequence": "spot_checked",
}
TRAINING_ROLES = {"dr_whole_spine", "dr_regional", "ct_axial", "ct_scout", "mr_sequence"}


@dataclass
class SeriesRecord:
    raw_relpath: str
    description: str
    acq_time: str
    series_number: int
    files: list[str]
    sizes: list[tuple[int, int]] = field(default_factory=list)
    uid: str = ""
    attrs: dict = field(default_factory=dict)


@dataclass
class StudyRecord:
    raw_relpath: str
    hospital_id: str
    patient_name: str
    exam_date: date
    acq_time: str
    series: list[SeriesRecord] = field(default_factory=list)
    uid: str = ""
    modality: str = ""


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[\s_\-+]+", text.upper()) if t}


def series_modality(description: str) -> str:
    upper = description.upper()
    if any(k in upper for k in MR_KEYWORDS):
        return "MR"
    if upper in DR_EXACT or any(k in upper for k in DR_KEYWORDS):
        return "DR"
    return "CT"


def _mode_size(sizes: list[tuple[int, int]]) -> tuple[int, int]:
    return Counter(sizes).most_common(1)[0][0] if sizes else (0, 0)


def classify_series(description: str, sizes: list[tuple[int, int]]) -> dict:
    """Return modality, role and descriptive attributes for one series."""
    upper = description.upper()
    tokens = _tokens(description)
    modality = series_modality(description)
    attrs = {
        "modality": modality, "role": "", "region": "", "view": "", "ct_kernel": "",
        "ct_slice_mm": "", "mr_weighting": "", "mr_plane": "", "mr_contrast": "",
        "mr_fat_suppressed": "",
    }
    width, height = _mode_size(sizes)

    if modality == "DR":
        if upper.startswith("DR LONG SPINE") or upper == "SPINE":
            attrs.update(role="dr_whole_spine", region="whole_spine")
        else:
            attrs["role"] = "dr_regional"
            for key, region in (("CERVICAL", "cervical"), ("THORACIC", "thoracic"),
                                ("LUMBAR", "lumbar"), ("CHEST", "chest"), ("PELVIS", "pelvis")):
                if key in upper:
                    attrs["region"] = region
                    break
            else:
                attrs["region"] = "trunk"
        if "AP" in tokens:
            attrs["view"] = "AP"
        elif "LATERAL" in tokens:
            attrs["view"] = "LAT"
    elif modality == "CT":
        if "AW ELECTRONIC FILM" in upper:
            attrs["role"] = "ct_rendered_film_aw"
        elif upper.startswith("DISPLAY"):
            attrs["role"] = "ct_rendered_film_display"
        elif upper.startswith("DOSE INFO"):
            attrs["role"] = "ct_dose_report"
        elif "SCOUT" in upper or (len(sizes) <= 10 and width != height):
            attrs["role"] = "ct_scout"
        else:
            attrs["role"] = "ct_axial"
            if "BONE" in tokens:
                attrs["ct_kernel"] = "bone"
            elif "STND" in tokens:
                attrs["ct_kernel"] = "standard"
            thickness = re.search(r"(\d+(?:\.\d+)?)\s*MM", upper)
            if thickness:
                attrs["ct_slice_mm"] = thickness.group(1)
    else:
        if "SCREEN SAVE" in upper:
            attrs["role"] = "mr_screen_save"
        elif "SURVEY" in upper or "LOC" in tokens:
            attrs["role"] = "mr_localizer"
        else:
            attrs["role"] = "mr_sequence"
            if "DWI" in upper:
                weighting = "DWI"
            elif "STIR" in upper:
                weighting = "STIR"
            elif "FLAIR" in upper:
                weighting = "T1_FLAIR" if "T1" in upper else "T2_FLAIR"
            elif re.search(r"(^|[^A-Z])E?PD[_ ]", upper):
                weighting = "PD"
            elif "T1" in upper or "LAVA" in upper or "FSPGR" in upper:
                weighting = "T1"
            elif "T2" in upper:
                weighting = "T2"
            else:
                weighting = "other"
            attrs["mr_weighting"] = weighting
            attrs["mr_contrast"] = int("+C" in upper.replace(" ", ""))
            attrs["mr_fat_suppressed"] = int(bool(tokens & {"SPAIR", "SPIR", "FS", "FAT", "WATER"}))
        if tokens & {"SAG", "OSAG"}:
            attrs["mr_plane"] = "sag"
        elif tokens & {"AX", "OAX", "TRA"}:
            attrs["mr_plane"] = "ax"
        elif tokens & {"COR", "OCOR"}:
            attrs["mr_plane"] = "cor"
        else:
            attrs["mr_plane"] = "unspecified"

    attrs["phi_burned_in"] = PHI_BY_ROLE[attrs["role"]]
    attrs["use_for_training"] = int(attrs["role"] in TRAINING_ROLES)
    return attrs


def dr_image_role(series_role: str, description: str, instance_index: int) -> str:
    """Role of one radiograph image.

    In ``Spine`` series the detector segments are numbered below 100 and the
    stitched whole-spine composites from 101 upward; ``DR Long Spine`` series
    contain only stitched composites.
    """
    if series_role != "dr_whole_spine":
        return "single_exposure"
    if description.upper().startswith("DR LONG SPINE") or instance_index >= 100:
        return "stitched_whole_spine"
    return "detector_segment"


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

def scan_raw_root(raw_root: Path, read_sizes: bool = True) -> list[StudyRecord]:
    studies: list[StudyRecord] = []
    for date_dir in sorted(p for p in raw_root.iterdir() if p.is_dir()):
        if not re.fullmatch(r"\d{8}", date_dir.name):
            raise ValueError(f"Unexpected top-level folder: {date_dir.name}")
        exam_date = date(int(date_dir.name[:4]), int(date_dir.name[4:6]), int(date_dir.name[6:]))
        for study_dir in sorted(p for p in date_dir.iterdir() if p.is_dir()):
            match = STUDY_DIR_RE.match(study_dir.name)
            if not match:
                raise ValueError(f"Unparseable study folder under {date_dir.name}")
            study = StudyRecord(
                raw_relpath=study_dir.relative_to(raw_root).as_posix(),
                hospital_id=match["hid"], patient_name=match["name"],
                exam_date=exam_date, acq_time=match["time"],
            )
            for series_dir_path in sorted(p for p in study_dir.iterdir() if p.is_dir()):
                smatch = SERIES_DIR_RE.match(series_dir_path.name)
                if not smatch:
                    raise ValueError(f"Unparseable series folder under {date_dir.name}")
                files = sorted(f.name for f in series_dir_path.iterdir()
                               if f.is_file() and INSTANCE_RE.match(f.name))
                series = SeriesRecord(
                    raw_relpath=series_dir_path.relative_to(raw_root).as_posix(),
                    description=smatch["desc"].strip(), acq_time=smatch["time"],
                    series_number=int(smatch["num"]), files=files,
                )
                if read_sizes:
                    for name in files:
                        with Image.open(series_dir_path / name) as im:
                            series.sizes.append(im.size)
                study.series.append(series)
            studies.append(study)
    return studies


# ---------------------------------------------------------------------------
# Linkage key and identifier assignment
# ---------------------------------------------------------------------------

def load_linkage_key(key_path: Path = DEFAULT_KEY_PATH) -> list[dict]:
    if not key_path.exists():
        return []
    with key_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _next_number(existing: list[str], prefix: str) -> int:
    numbers = [int(x[len(prefix):]) for x in existing if x.startswith(prefix) and x[len(prefix):].isdigit()]
    return max(numbers, default=0) + 1


def assign_identifiers(studies: list[StudyRecord], key_rows: list[dict]) -> list[dict]:
    """Assign stable pseudonymous ids in place and return the updated key."""
    patient_by_hid = {r["hospital_id"]: r["pseudo_id"] for r in key_rows if r["level"] == "patient"}
    uid_by_path = {r["raw_relpath"]: r["pseudo_id"] for r in key_rows if r["level"] in ("study", "series")}
    rows_by_id = {r["pseudo_id"]: dict(r) for r in key_rows}

    names_by_hid: dict[str, set[str]] = defaultdict(set)
    first_seen: dict[str, tuple] = {}
    for study in studies:
        names_by_hid[study.hospital_id].add(study.patient_name)
        order = (study.exam_date, study.acq_time)
        first_seen[study.hospital_id] = min(first_seen.get(study.hospital_id, order), order)
    conflicts = {hid: names for hid, names in names_by_hid.items() if len(names) > 1}
    if conflicts:
        raise ValueError(f"{len(conflicts)} hospital id(s) map to more than one patient name")

    prefix = SITE_CODE
    next_patient = _next_number(list(patient_by_hid.values()), prefix)
    for hid in sorted(first_seen, key=lambda h: (first_seen[h], h)):
        if hid not in patient_by_hid:
            pid = f"{prefix}{next_patient:03d}"
            next_patient += 1
            patient_by_hid[hid] = pid
            rows_by_id[pid] = {"level": "patient", "pseudo_id": pid, "parent_id": "",
                               "hospital_id": hid, "patient_name": next(iter(names_by_hid[hid])),
                               "exam_date": "", "raw_relpath": ""}

    by_patient: dict[str, list[StudyRecord]] = defaultdict(list)
    for study in studies:
        by_patient[patient_by_hid[study.hospital_id]].append(study)
    for pid, patient_studies in by_patient.items():
        existing = [uid_by_path[s.raw_relpath] for s in patient_studies if s.raw_relpath in uid_by_path]
        existing += [r["pseudo_id"] for r in rows_by_id.values() if r["level"] == "study" and r["parent_id"] == pid]
        next_study = _next_number(existing, f"{pid}_st")
        for study in sorted(patient_studies, key=lambda s: (s.exam_date, s.acq_time)):
            if study.raw_relpath not in uid_by_path:
                uid = f"{pid}_st{next_study:02d}"
                next_study += 1
                uid_by_path[study.raw_relpath] = uid
                rows_by_id[uid] = {"level": "study", "pseudo_id": uid, "parent_id": pid, "hospital_id": "",
                                   "patient_name": "", "exam_date": study.exam_date.isoformat(),
                                   "raw_relpath": study.raw_relpath}
            study.uid = uid_by_path[study.raw_relpath]
            existing_series = [r["pseudo_id"] for r in rows_by_id.values()
                               if r["level"] == "series" and r["parent_id"] == study.uid]
            next_series = _next_number(existing_series, f"{study.uid}_se")
            for series in sorted(study.series, key=lambda s: (s.series_number, s.description)):
                if series.raw_relpath not in uid_by_path:
                    uid = f"{study.uid}_se{next_series:02d}"
                    next_series += 1
                    uid_by_path[series.raw_relpath] = uid
                    rows_by_id[uid] = {"level": "series", "pseudo_id": uid, "parent_id": study.uid,
                                       "hospital_id": "", "patient_name": "", "exam_date": "",
                                       "raw_relpath": series.raw_relpath}
                series.uid = uid_by_path[series.raw_relpath]

    level_order = {"patient": 0, "study": 1, "series": 2}
    return sorted(rows_by_id.values(), key=lambda r: (r["pseudo_id"].split("_")[0], level_order[r["level"]], r["pseudo_id"]))


def default_raw_root() -> Path:
    """Return the locally configured raw export folder."""
    configured = os.environ.get(RAW_ROOT_ENV)
    if configured:
        return Path(configured)
    if RAW_ROOT_POINTER.exists():
        return REPO_ROOT / RAW_ROOT_POINTER.read_text(encoding="utf-8").strip()
    raise FileNotFoundError(f"Set {RAW_ROOT_ENV} or create {RAW_ROOT_POINTER}")


def series_dir(series_uid: str, key_path: Path = DEFAULT_KEY_PATH, raw_root: Path | None = None) -> Path:
    """Resolve a pseudonymous series id to its raw image folder."""
    for row in load_linkage_key(key_path):
        if row["level"] == "series" and row["pseudo_id"] == series_uid:
            return (raw_root or default_raw_root()) / row["raw_relpath"]
    raise KeyError(series_uid)


# ---------------------------------------------------------------------------
# Manifest construction
# ---------------------------------------------------------------------------

def _patient_id(uid: str) -> str:
    return uid.split("_")[0]


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_tables(studies: list[StudyRecord], raw_root: Path) -> dict[str, list[dict]]:
    first_date: dict[str, date] = {}
    for study in studies:
        pid = _patient_id(study.uid)
        first_date[pid] = min(first_date.get(pid, study.exam_date), study.exam_date)

    series_rows, study_rows, dr_rows = [], [], []
    for study in sorted(studies, key=lambda s: s.uid):
        pid = _patient_id(study.uid)
        by_number = {s.series_number: s for s in study.series}
        modalities = Counter()
        for series in sorted(study.series, key=lambda s: s.uid):
            attrs = classify_series(series.description, series.sizes)
            series.attrs = attrs
            modalities[attrs["modality"]] += 1
            width, height = _mode_size(series.sizes)
            # Philips exports a processed copy of an acquisition with an "e" prefix
            # and the source series number plus one; acquisition times can differ.
            source = by_number.get(series.series_number - 1)
            derived_from = ""
            if (attrs["modality"] == "MR" and re.match(r"^e+[A-Z]", series.description)
                    and source is not None and not re.match(r"^e+[A-Z]", source.description)):
                derived_from = source.uid
            series_rows.append({
                "series_uid": series.uid, "study_uid": study.uid, "patient_pid": pid,
                "modality": attrs["modality"], "role": attrs["role"],
                "series_description": series.description, "series_number": series.series_number,
                "n_images": len(series.files), "width": width, "height": height,
                "n_distinct_sizes": len(set(series.sizes)),
                "region": attrs["region"], "view": attrs["view"],
                "ct_kernel": attrs["ct_kernel"], "ct_slice_mm": attrs["ct_slice_mm"],
                "mr_weighting": attrs["mr_weighting"], "mr_plane": attrs["mr_plane"],
                "mr_contrast": attrs["mr_contrast"], "mr_fat_suppressed": attrs["mr_fat_suppressed"],
                "derived_from": derived_from,
                "phi_burned_in": attrs["phi_burned_in"], "use_for_training": attrs["use_for_training"],
            })
            if attrs["modality"] == "DR":
                seen: dict[str, str] = {}
                for name, (w, h) in zip(series.files, series.sizes):
                    match = INSTANCE_RE.match(name)
                    index = int(match["idx"])
                    copy = int(match["copy"] or 1)
                    image_uid = f"{series.uid}_im{index:03d}" + (f"c{copy}" if copy > 1 else "")
                    checksum = _md5(raw_root / series.raw_relpath / name)
                    dr_rows.append({
                        "image_uid": image_uid, "series_uid": series.uid, "patient_pid": pid,
                        "file_name": name, "instance_index": index,
                        "image_role": dr_image_role(attrs["role"], series.description, index),
                        "region": attrs["region"], "view": attrs["view"],
                        "width": w, "height": h, "aspect_h_over_w": round(h / w, 3),
                        "md5": checksum, "duplicate_of": seen.get(checksum, ""),
                    })
                    seen.setdefault(checksum, image_uid)
        if len(modalities) != 1:
            raise ValueError(f"Study {study.uid} mixes modalities: {dict(modalities)}")
        study.modality = next(iter(modalities))
        study_rows.append({
            "study_uid": study.uid, "patient_pid": pid, "modality": study.modality,
            "exam_year": study.exam_date.year,
            "day_offset": (study.exam_date - first_date[pid]).days,
            "n_series": len(study.series),
            "n_training_series": sum(s.attrs["use_for_training"] for s in study.series),
            "n_images": sum(len(s.files) for s in study.series),
        })

    patient_rows = []
    by_patient: dict[str, list[StudyRecord]] = defaultdict(list)
    for study in studies:
        by_patient[_patient_id(study.uid)].append(study)

    def dates_with(patient_studies, roles):
        return sorted({s.exam_date for s in patient_studies
                       if any(x.attrs["role"] in roles for x in s.series)})

    def min_gap(a, b):
        return min((abs((x - y).days) for x in a for y in b), default="")

    for pid in sorted(by_patient):
        patient_studies = by_patient[pid]
        roles = Counter(x.attrs["role"] for s in patient_studies for x in s.series)
        images = Counter()
        for s in patient_studies:
            for x in s.series:
                if x.attrs["use_for_training"]:
                    images[x.attrs["modality"]] += len(x.files)
        dr_dates = dates_with(patient_studies, {"dr_whole_spine", "dr_regional"})
        ct_dates = dates_with(patient_studies, {"ct_axial"})
        mr_dates = dates_with(patient_studies, {"mr_sequence"})
        exam_dates = sorted(s.exam_date for s in patient_studies)
        stitched = sum(1 for r in dr_rows if r["patient_pid"] == pid
                       and r["image_role"] == "stitched_whole_spine" and not r["duplicate_of"])
        patient_rows.append({
            "patient_pid": pid, "n_studies": len(patient_studies),
            "first_exam_year": exam_dates[0].year,
            "followup_days": (exam_dates[-1] - exam_dates[0]).days,
            "has_dr": int(bool(dr_dates)), "has_dr_whole_spine": int(roles["dr_whole_spine"] > 0),
            "n_dr_stitched_whole_spine": stitched,
            "has_ct_axial": int(bool(ct_dates)), "has_ct_scout": int(roles["ct_scout"] > 0),
            "has_mr": int(bool(mr_dates)),
            "n_dr_images": images["DR"], "n_ct_images": images["CT"], "n_mr_images": images["MR"],
            "min_gap_days_dr_ct": min_gap(dr_dates, ct_dates),
            "min_gap_days_dr_mr": min_gap(dr_dates, mr_dates),
        })

    return {"patients": patient_rows, "studies": study_rows, "series": series_rows, "dr_images": dr_rows}


def _write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0]) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def render_readme(tables: dict[str, list[dict]]) -> str:
    patients, series, dr_rows = tables["patients"], tables["series"], tables["dr_images"]
    by_modality = defaultdict(lambda: Counter())
    for row in series:
        by_modality[row["modality"]]["series"] += 1
        by_modality[row["modality"]]["images"] += row["n_images"]
        by_modality[row["modality"]]["training_series"] += row["use_for_training"]
    role_counts = Counter(row["role"] for row in series)
    role_images = Counter()
    for row in series:
        role_images[row["role"]] += row["n_images"]
    image_roles = Counter(r["image_role"] for r in dr_rows if not r["duplicate_of"])
    duplicates = sum(1 for r in dr_rows if r["duplicate_of"])

    def count(flag):
        return sum(1 for p in patients if p[flag])

    paired_ct = [p for p in patients if p["has_dr"] and p["has_ct_axial"]]
    paired_mr = [p for p in patients if p["has_dr"] and p["has_mr"]]
    paired_ws_ct = [p for p in patients if p["has_dr_whole_spine"] and p["has_ct_axial"]]
    all_three = [p for p in patients if p["has_dr"] and p["has_ct_axial"] and p["has_mr"]]
    gaps_ct = sorted(p["min_gap_days_dr_ct"] for p in paired_ct)
    gaps_mr = sorted(p["min_gap_days_dr_mr"] for p in paired_mr)
    years = Counter(p["first_exam_year"] for p in patients)

    def gap_summary(gaps):
        if not gaps:
            return "n/a"
        return (f"median {gaps[len(gaps) // 2]} d, range {gaps[0]}-{gaps[-1]} d, "
                f"same day {sum(g == 0 for g in gaps)}, within 30 d {sum(g <= 30 for g in gaps)}")

    lines = [
        "# Scoliosis imaging: pseudonymized manifest",
        "",
        "Entry point for experiments on the scoliosis imaging export received from a",
        "collaborating hospital (site code `SC`).",
        "This README holds aggregate counts only; the per-patient CSV files in this",
        "folder are excluded from version control by the repository ignore rules.",
        "",
        "Regenerate (from `src/`): `python -m scoliosis_exp.manifest`.",
        "Resolve images: `scoliosis_exp.manifest.series_dir(series_uid)`.",
        "",
        "## Cohort",
        "",
        f"- Patients: {len(patients)}; studies: {len(tables['studies'])}; series: {len(series)}; "
        f"images: {sum(r['n_images'] for r in series)}.",
        f"- First-exam year distribution: "
        + ", ".join(f"{y}: {n}" for y, n in sorted(years.items())) + ".",
        "- Every patient in the export is a scoliosis patient; there are no negative controls.",
        "- No diagnostic labels (Cobb angle, curve type, surgical status) are included.",
        "",
        "| Modality | Series | Training-eligible series | Images |",
        "|---|---:|---:|---:|",
    ]
    for modality in ("DR", "CT", "MR"):
        c = by_modality[modality]
        lines.append(f"| {modality} | {c['series']} | {c['training_series']} | {c['images']} |")
    lines += [
        "",
        "## Same-patient pairing",
        "",
        f"- Radiograph (any) + CT axial: {len(paired_ct)} patients; gap between nearest exams: {gap_summary(gaps_ct)}.",
        f"- Whole-spine radiograph + CT axial: {len(paired_ws_ct)} patients.",
        f"- Radiograph + MR: {len(paired_mr)} patients; gap: {gap_summary(gaps_mr)}.",
        f"- Radiograph + CT axial + MR: {len(all_three)} patients.",
        f"- Patients with a CT scout (AP/lateral topogram): {count('has_ct_scout')}.",
        f"- Patients with at least one stitched whole-spine radiograph: "
        f"{sum(1 for p in patients if p['n_dr_stitched_whole_spine'] > 0)}.",
        "",
        "## Series roles",
        "",
        "| Role | Series | Images | Burned-in identifiers | Training-eligible |",
        "|---|---:|---:|---|---|",
    ]
    for role in sorted(role_counts):
        lines.append(f"| `{role}` | {role_counts[role]} | {role_images[role]} | {PHI_BY_ROLE[role]} | "
                     f"{'yes' if role in TRAINING_ROLES else 'no'} |")
    lines += [
        "",
        f"Radiograph images (excluding {duplicates} byte-identical duplicates): "
        + ", ".join(f"{k} {v}" for k, v in sorted(image_roles.items())) + ".",
        "",
        "## Data limitations",
        "",
        "- The export is 8-bit JPEG after display windowing: no Hounsfield units, pixel spacing,",
        "  slice thickness, patient orientation or acquisition parameters are available. CT window",
        "  settings differ between series (bone, soft tissue, lung). DICOM originals should replace",
        "  these images for quantitative work.",
        "- CT coverage differs between patients (cervical, chest, thoracolumbar); the scout series",
        "  shows the scanned range.",
        "- Radiograph view (AP versus lateral) is known only when the series description states it;",
        "  stitched whole-spine series contain both views without a per-image tag.",
        "",
        "## Privacy",
        "",
        "- Pseudonymous identifiers: patient `SCnnn`, study `SCnnn_stNN`, series `SCnnn_stNN_seNN`,",
        "  radiograph image `<series>_imNNN`. Studies are numbered chronologically per patient at",
        "  first assignment; identifiers never change once assigned.",
        "- Exact dates are replaced by the exam year and the day offset from the patient's first exam.",
        "- The linkage key (pseudonymous id to hospital id and raw path) is stored next to the raw",
        "  data under `data/` and is not under version control. Do not copy it elsewhere.",
        "- `ct_rendered_film_aw` and `ct_dose_report` series show the patient name, hospital id, birth",
        "  date, exam date or study id in the pixels; never use them in training data or figures.",
        "- `phi_burned_in` values come from a visual review on 2026-11-01: `not_observed` means one",
        "  image of every series in that role was inspected; `spot_checked` means a sample of series",
        "  was inspected. Re-check any image before it appears in a publication figure.",
        "- Publication use requires documented ethics approval and a data use agreement.",
        "",
        "## Files",
        "",
        "- `patients.csv`: one row per patient (modality availability, image counts, minimum day gap",
        "  between radiograph and CT/MR exams, follow-up span).",
        "- `studies.csv`: one row per study (modality, exam year, day offset, series and image counts).",
        "- `series.csv`: one row per series (role, description, series number, image count, dominant",
        "  size, region/view for DR, kernel/slice thickness for CT, weighting/plane/contrast/fat",
        "  suppression for MR, `derived_from` linking Philips `e`-prefixed derived series to their",
        "  source acquisition, `phi_burned_in`, `use_for_training`).",
        "- `dr_images.csv`: one row per radiograph image (detector segment, stitched whole-spine",
        "  composite or single exposure; size; MD5; `duplicate_of` for byte-identical copies).",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--raw-root", type=Path, default=None)
    parser.add_argument("--key", type=Path, default=DEFAULT_KEY_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    raw_root = args.raw_root or default_raw_root()
    studies = scan_raw_root(raw_root)
    key_rows = assign_identifiers(studies, load_linkage_key(args.key))
    _write_csv(args.key, key_rows, KEY_FIELDS)
    tables = build_tables(studies, raw_root)
    for name, rows in tables.items():
        _write_csv(args.out_dir / f"{name}.csv", rows)
    (args.out_dir / "README.md").write_text(render_readme(tables), encoding="utf-8")
    print(f"patients={len(tables['patients'])} studies={len(tables['studies'])} "
          f"series={len(tables['series'])} dr_images={len(tables['dr_images'])}")
    print(f"manifest -> {args.out_dir}")
    print(f"linkage key (private) -> {args.key}")


if __name__ == "__main__":
    main()
