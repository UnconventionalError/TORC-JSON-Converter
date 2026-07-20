# TORC `paths.json` → Jedipedia Converter

## What This Does

Searches a folder (and every subfolder inside it) for files named `paths.json` in the old TORC format, converts each one to the newer Jedipedia format, and saves the results into one export folder.

Each output file is named after the folder the `paths.json` came from.

**Example**

A `paths.json` inside a folder called `Sith Lord` becomes: `Sith Lord.json`

`paths.json` commonly sits inside a folder literally called `assets`. If so, that `assets` folder is skipped and the folder **above it** is used for the filename instead.

Example:

```text
.../Sith Lord/Sith Lord Armor/assets/paths.json → Sith Lord Armor.json
```

If two different `paths.json` files would end up with the **same output filename**, the tool automatically climbs one folder higher for **both** until they're unique.

Example:

```text
.../Republic/Officer/assets/paths.json  → Republic Officer.json
.../Empire/Officer/assets/paths.json → Empire Officer.json
```

The output filename (without `.json`) is also used to populate `meta.charName`, since TORC files don't contain a character name.

A note is added to `meta.logging` explaining that the name was assumed from the folder structure, making it easy to find and correct later if needed.

Every converted file's `meta` block also includes:

- `"TORC Conversion"`
- Any warnings generated during conversion (for example, a missing eye material path or an undetectable body type).

---

# One-Time Setup

1. Install Python 3 if you don't already have it:

   https://www.python.org/downloads/

### Windows

- During installation, tick **"Add Python to PATH"**.

### macOS

- The installer from python.org includes everything needed (including the built-in Tk toolkit used for the program window).

No additional downloads or packages are required.

---

# How To Run

Either:

- Double-click `TORC_to_Jedipedia_Converter.py`

  > On Windows this will usually launch Python automatically.
  >
  > If it opens in a text editor instead:
  >
  > **Right-click → Open With → Python**

Or run it from a terminal in the project folder:

```bash
python TORC_to_Jedipedia_Converter.py
```

---

# How To Use

1. Click **Choose Source Folder...**
   - Select the top-level folder containing your `paths.json` files.
   - Every subfolder is searched automatically.

2. Click **Choose Export Folder...**
   - Choose where the converted Jedipedia files will be written.

3. *(Optional)* Enable **Preserve source folder structure in export** if you want the export folder to mirror the original folder tree instead of placing every file into one folder.

4. Click **Convert All**.

5. Watch the log window for progress.

   Any file with a warning will display a line beginning with: `⚠`

   The same warning is also saved into that file's `meta.logging` list.

6. When conversion finishes, click **Open Export Folder**.

---

# Export Modes

## Flat Export (Default)

Every converted file is written directly into the export folder.

Filenames are automatically disambiguated if duplicates would occur.

---

## Preserve Folder Structure

The export folder mirrors your original source tree.

Each `assets/paths.json` is replaced with a single `.json` file named after the folder it lived in.

That file is placed in the **parent** folder.

### Example

**Source**

```text
Imperial Army/
└── Captain Smith/
    ├── Captain Smith Body/
    │   └── assets/
    │       └── paths.json
    └── Captain Smith Uniform/
        └── assets/
            └── paths.json
```

**Export**

```text
Imperial Army/
└── Captain Smith/
    ├── Captain Smith Body.json
    └── Captain Smith Uniform.json
```

Characters with only one variant work the same way.

### Source

```text
Imperial Army/
└── Major Green Armored/
    └── assets/
        └── paths.json
```

### Export

```text
Imperial Army/
└── Major Green Armored.json
```

This avoids unnecessary folders containing only a single file.

Since every file stays within its original folder hierarchy, duplicate names (such as multiple `Officer` folders) never conflict.

---

# Files Included

| File | Description |
|------|-------------|
| `TORC_to_Jedipedia_Converter.py` | Run this file. |
| `converter.py` | Contains the conversion logic. Keep this file alongside the main program. |
| `README.md` | This documentation. |

---

# What Gets Converted?

Every output file receives a new `meta` block.

| Field | Value |
|-------|-------|
| `charType` | Always `"unknown"` |
| `charName` | Taken from the output filename |
| `nppPath` | Left blank |
| `bodyType` | Automatically detected from model filenames where possible (e.g. `bfn`, `bmn`) |
| `logging` | Contains `"TORC Conversion"` plus any warnings generated during conversion |

Additional conversion rules:

- Numeric values (colour palettes, specular values, etc.) are converted into text strings exactly as written.
- Fields inside each `otherValues` block are reordered to match the Jedipedia format.
- Hair slots missing a `directionMap` automatically receive:

```text
/art/defaultassets/black.dds
```

- Eye materials missing a `matPath` automatically receive:

```text
/art/shaders/materials/eye_human_non_a01_c01.mat
```

Whenever the converter has to insert a default value or make an assumption, an explanatory note is added to `meta.logging`.
