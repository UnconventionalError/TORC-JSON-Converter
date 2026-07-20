"""
TORC paths.json -> Jedipedia .json converter
Core conversion logic (no GUI code lives here, so it can be reused/tested standalone).
"""

import json
import re
from pathlib import Path

DEFAULT_EYE_MAT_PATH = "/art/shaders/materials/eye_human_non_a01_c01.mat"
DEFAULT_DIRECTION_MAP = "/art/defaultassets/black.dds"

# Canonical key order Jedipedia uses inside an "otherValues" block.
OTHER_VALUES_ORDER = [
    "derived",
    "flush",
    "fleshBrightness",
    "palette1",
    "palette1Specular",
    "palette1MetallicSpecular",
    "palette2",
    "palette2Specular",
    "palette2MetallicSpecular",
]

# Heuristic pattern for body-type codes like "bmn", "bfn", "hmn", "hfs" etc.
# first letter: body group, second letter: gender, third letter: build.
BODY_TYPE_PATTERN = re.compile(r"_([a-z][mf][a-z])_")


class ConversionResult:
    def __init__(self, filename, data, errors, source_path):
        self.filename = filename
        self.data = data
        self.errors = errors
        self.source_path = source_path


def load_torc_json(path: Path):
    """
    Load a TORC paths.json file, converting every JSON number to a string
    using its exact original text (no float round-tripping), per project spec.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f, parse_float=str, parse_int=str)


def reorder_other_values(other_values: dict) -> dict:
    """Return a new dict with otherValues keys in Jedipedia's canonical order.
    Any keys not in the canonical list are appended afterwards, in their
    original order, so nothing is ever silently dropped."""
    if not isinstance(other_values, dict):
        return other_values

    ordered = {}
    for key in OTHER_VALUES_ORDER:
        if key in other_values:
            ordered[key] = other_values[key]
    for key, value in other_values.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def detect_body_type(slots) -> str:
    """
    Scan every "models" array in the document for a recurring body-type
    code (e.g. "bfn", "bmn"). Returns the most common match, or "" if
    nothing confident is found.
    """
    counts = {}
    for slot in slots:
        models = slot.get("models") if isinstance(slot, dict) else None
        if not isinstance(models, list):
            continue
        for model_path in models:
            if not isinstance(model_path, str):
                continue
            for match in BODY_TYPE_PATTERN.findall(model_path):
                counts[match] = counts.get(match, 0) + 1

    if not counts:
        return ""

    best_code, best_count = max(counts.items(), key=lambda kv: kv[1])
    # Require it to show up more than once so a one-off filename fluke
    # doesn't get promoted to "the" body type.
    if best_count >= 2:
        return best_code
    return ""


def fix_hair_direction_map(slot: dict, errors: list):
    """Hair and facehair entries must have a directionMap in ddsPaths;
    add the default if it's missing."""
    slot_name = slot.get("slotName")
    if slot_name not in ("hair", "facehair"):
        return
    material_info = slot.get("materialInfo")
    if not isinstance(material_info, dict):
        return
    dds_paths = material_info.get("ddsPaths")
    if not isinstance(dds_paths, dict):
        return
    if "directionMap" not in dds_paths:
        dds_paths["directionMap"] = DEFAULT_DIRECTION_MAP
        errors.append(
            f"Added default directionMap for '{slot_name}' slot (missing in source)."
        )


def fix_eye_mat_path(material_info: dict, slot_name: str, errors: list):
    """eyeMatInfo needs a matPath; TORC files don't have one, so insert the
    known default and log it."""
    if not isinstance(material_info, dict):
        return
    eye_info = material_info.get("eyeMatInfo")
    if not isinstance(eye_info, dict):
        return
    if not eye_info.get("matPath"):
        eye_info["matPath"] = DEFAULT_EYE_MAT_PATH
        errors.append(
            f"Using default eye material path for eyeMatInfo.matPath "
            f"(slot: {slot_name})."
        )


def normalize_other_values_recursive(obj, errors, slot_name_hint=""):
    """
    Walk the structure. Wherever we find a dict that looks like an
    'otherValues' block (has a 'derived' key), reorder its keys.
    Also handles eyeMatInfo.matPath default insertion along the way.
    """
    if isinstance(obj, dict):
        # Reorder this dict in place if it's an otherValues-shaped block.
        if "derived" in obj:
            reordered = reorder_other_values(obj)
            obj.clear()
            obj.update(reordered)

        # Catch eyeMatInfo wherever it appears (normally under materialInfo).
        if "eyeMatInfo" in obj:
            fix_eye_mat_path(obj, slot_name_hint, errors)

        for value in obj.values():
            normalize_other_values_recursive(value, errors, slot_name_hint)

    elif isinstance(obj, list):
        for item in obj:
            normalize_other_values_recursive(item, errors, slot_name_hint)


def convert_slots(raw_slots, errors):
    """Apply all structural fixes to the list of slot objects from the
    source TORC file. Mutates and returns the same list."""
    if not isinstance(raw_slots, list):
        errors.append(
            "Source file's top level was not a list of slots as expected; "
            "output may be incomplete."
        )
        return []

    for slot in raw_slots:
        if not isinstance(slot, dict):
            errors.append("Found a slot entry that wasn't an object; skipped.")
            continue

        slot_name = slot.get("slotName", "<unknown>")

        if "slotName" not in slot:
            errors.append("A slot entry was missing 'slotName'.")
        if "materialInfo" not in slot:
            errors.append(f"Slot '{slot_name}' was missing 'materialInfo'.")

        fix_hair_direction_map(slot, errors)
        normalize_other_values_recursive(slot, errors, slot_name_hint=slot_name)

    return raw_slots


def build_meta_block(slots, errors, assumed_char_name="") -> dict:
    body_type = detect_body_type(slots)
    if not body_type:
        errors.append("Could not auto-detect bodyType; left blank.")

    if assumed_char_name:
        errors.append(
            f"Character name assumed from folder structure: '{assumed_char_name}'."
        )

    # "TORC Conversion" note always goes in first, per project spec.
    combined_errors = ["TORC Conversion"] + errors

    return {
        "slotName": "meta",
        "charType": "unknown",
        "charName": assumed_char_name,
        "nppPath": "",
        "bodyType": body_type,
        "errors": [],
        "logging": combined_errors,
    }


def convert_paths_json(source_path: Path, assumed_char_name: str = "") -> ConversionResult:
    """Convert a single TORC paths.json file into Jedipedia-format data.
    Never raises for recoverable issues -- problems are collected into
    the returned errors list (and end up in the meta.errors block) so a
    batch run can keep going.

    assumed_char_name: the output filename (without extension) that this
    file will be saved as, used to pre-fill meta.charName since TORC
    files carry no character name of their own.
    """
    errors = []
    try:
        raw = load_torc_json(source_path)
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"Failed to read/parse file: {exc}")
        raw = []

    slots = convert_slots(raw, errors)
    meta = build_meta_block(slots, errors, assumed_char_name=assumed_char_name)

    data = [meta] + slots
    return ConversionResult(filename=None, data=data, errors=errors, source_path=source_path)


def sanitize_filename(name: str) -> str:
    """Strip characters that are illegal in Windows/Mac filenames."""
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", name).strip()
    return cleaned or "Unnamed"


def find_paths_json_files(root: Path):
    """Recursively find every file named paths.json (case-insensitive)
    under root."""
    results = []
    for p in root.rglob("*"):
        if p.is_file() and p.name.lower() == "paths.json":
            results.append(p)
    return results


def _naming_start_dir(path: Path) -> Path:
    """The folder a paths.json's name should be based on. Since paths.json
    commonly lives inside an "assets" folder, skip past that and use its
    parent instead."""
    parent = path.parent
    if parent.name.lower() == "assets" and parent.parent is not None:
        return parent.parent
    return parent


def _ancestor_chain(start_dir: Path):
    """List of folder names from start_dir upward to the filesystem root,
    e.g. Path('.../Republic/Officer') -> ['Officer', 'Republic', ...]."""
    chain = []
    seen = set()
    cur = start_dir
    while cur is not None and cur.name and str(cur) not in seen:
        chain.append(cur.name)
        seen.add(str(cur))
        if cur.parent == cur:
            break
        cur = cur.parent
    return chain


def assign_output_paths_preserving_structure(paths, source_root: Path):
    """
    Like assign_output_names, but instead of flattening everything into a
    single export folder, mirrors each file's folder location relative to
    source_root.

    The "assets" folder (if present) is skipped, same as in flat mode.
    On top of that, the leaf folder that held the paths.json (e.g.
    "Captain Smith Body") is collapsed into a single output file placed
    in ITS PARENT folder, rather than kept as a wrapping folder of its
    own. This means multiple variant folders for the same character
    (Body, Uniform, Uniform 2, ...) all end up grouped together as
    sibling files inside their shared parent folder:

        .../Imperial Army/Captain Smith/Captain Smith Body/assets/paths.json
        .../Imperial Army/Captain Smith/Captain Smith Uniform/assets/paths.json
    becomes:
        .../Imperial Army/Captain Smith/Captain Smith Body.json
        .../Imperial Army/Captain Smith/Captain Smith Uniform.json

    And a character with only one variant folder (no separate
    Body/Uniform split) loses its redundant self-named wrapper folder
    the same way:
        .../Imperial Army/Major Green Armored/assets/paths.json
    becomes:
        .../Imperial Army/Major Green Armored.json

    Returns a list of (source_path, output_relative_path) where
    output_relative_path is a Path relative to the export root (it may
    include subfolders -- create them with mkdir(parents=True) before
    writing).
    """
    entries = []
    for p in paths:
        naming_dir = _naming_start_dir(p)
        base_name = sanitize_filename(naming_dir.name) or "Unnamed"

        if naming_dir == source_root:
            # paths.json sits at (or immediately under "assets" of) the
            # source root itself -- nothing above it to group under.
            rel_dir = Path(".")
        else:
            rel_dir = naming_dir.parent.relative_to(source_root)

        entries.append((p, rel_dir, base_name))

    # Guard against two different source files landing on the same
    # folder + name (e.g. two separately-named trees that happen to
    # produce the same grouping folder and leaf name).
    used = {}
    results = []
    for p, rel_dir, base_name in entries:
        key = (str(rel_dir).lower(), base_name.lower())
        if key not in used:
            used[key] = 1
            filename = f"{base_name}.json"
        else:
            used[key] += 1
            filename = f"{base_name} ({used[key]}).json"
        results.append((p, rel_dir / filename))
    return results


def assign_output_names(paths):
    """
    Decide the output filename for each found paths.json path.

    The base folder used for naming is the paths.json's parent folder,
    unless that parent is literally called "assets" (case-insensitive),
    in which case the grandparent folder is used instead.

    On a naming collision between two files, one more ancestor folder is
    prepended to *both* colliding names, and this repeats up the folder
    tree until the names are unique (or ancestors run out, in which case
    a numeric suffix is used as a last resort).

    Returns a list of (source_path, output_filename) in the same order
    as the input list.
    """
    start_dirs = [_naming_start_dir(p) for p in paths]
    chains = [_ancestor_chain(d) for d in start_dirs]

    n = len(paths)
    level = [1] * n  # how many folder names (from the bottom) to use

    def name_for(i):
        parts = chains[i][: level[i]]
        return " ".join(reversed(parts)).strip()

    # Repeatedly extend the level of any names that collide, until stable.
    changed = True
    while changed:
        changed = False
        groups = {}
        for i in range(n):
            groups.setdefault(name_for(i), []).append(i)
        for indices in groups.values():
            if len(indices) > 1:
                for i in indices:
                    if level[i] < len(chains[i]):
                        level[i] += 1
                        changed = True

    base_names = [sanitize_filename(name_for(i)) or "Unnamed" for i in range(n)]

    # Last-resort numeric suffix for any names still colliding
    # (ran out of ancestor folders to disambiguate with).
    used = {}
    output_names = []
    for base in base_names:
        if base not in used:
            used[base] = 1
            output_names.append(f"{base}.json")
        else:
            used[base] += 1
            output_names.append(f"{base} ({used[base]}).json")

    return list(zip(paths, output_names))