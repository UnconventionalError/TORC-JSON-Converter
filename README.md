# TORC paths.json -> Jedipedia Converter
=======================================

WHAT THIS DOES
--------------
Searches a folder (and every subfolder inside it) for files named
"paths.json" in the old TORC format, converts each one to the newer
Jedipedia format, and saves the results into one export folder.

Each output file is named after the folder the paths.json came from.
Example: a paths.json inside a folder called "Sith Lord" becomes
"Sith Lord.json".

paths.json commonly sits inside a folder literally called "assets" - if
so, that "assets" folder is skipped and the folder ABOVE it is used for
the name instead. Example:
    .../Sith Lord/Sith Lord Armor/assets/paths.json  ->  "Sith Lord Armor.json"

If two different paths.json files would end up with the SAME output
name, the tool automatically climbs one folder higher for BOTH of them
to tell them apart, repeating as many times as needed, e.g.:
    .../Republic/Officer/assets/paths.json -> "Republic Officer.json"
    .../Empire/Officer/assets/paths.json   -> "Empire Officer.json"

The output filename (without ".json") is also used to fill in that
file's meta.charName, since TORC files don't carry a character name of
their own. A note is added to meta.errors explaining that the name was
assumed from the folder structure, so it's easy to spot and correct by
hand if it's ever wrong.

Every converted file's meta block includes a note that it was a
"TORC Conversion", plus any other warnings about things the converter
had to guess or fill in (like a missing eye material path, or a body
type it couldn't detect).


ONE-TIME SETUP
---------------
1. Install Python 3, if you don't already have it:
   https://www.python.org/downloads/
   - Windows: during install, tick the box "Add Python to PATH".
   - Mac: the installer from python.org includes everything needed
     (the built-in "Tk" toolkit this program's window uses).

That's it - no other downloads or installs needed.


HOW TO RUN
----------
- Double-click "TORC_to_Jedipedia_Converter.py".
  (On Windows this usually opens it directly. If it opens in a text
  editor instead, right-click the file -> "Open with" -> Python.)

  OR, from a terminal/command prompt, in this folder run:
      python TORC_to_Jedipedia_Converter.py


HOW TO USE
----------
1. Click "Choose Source Folder..." and select the top-level folder that
   contains your paths.json files anywhere inside it (subfolders are
   searched automatically).
2. Click "Choose Export Folder..." and select where you want the
   converted Jedipedia .json files saved.
3. (Optional) Tick "Preserve source folder structure in export" if you
   want the export folder to mirror your original folder tree, rather
   than dumping every converted file flat into one folder. See below
   for exactly how this works.
4. Click "Convert All".
5. Watch the log at the bottom for progress. Any file with a warning
   will show a line starting with "⚠" - that same note is also saved
   inside that file's own meta.errors list, so it's never lost.
6. When it's done, click "Open Export Folder" to see your results.


EXPORT MODES
------------
Flat (default, checkbox unticked):
  Every converted file is saved directly into the export folder, named
  after its source folder (with automatic disambiguation - see below).

Preserve folder structure (checkbox ticked):
  The export folder mirrors your source folder tree. Each paths.json's
  "assets" folder (and the generic "paths.json" filename) is replaced
  with a single file named after the folder it lived in, and that file
  is placed in the PARENT of that folder - so if a character has
  several variant folders (Body, Uniform, Uniform 2, etc.), they all
  end up grouped together as sibling files in one shared folder.
  Example:
      Source:
        .../Imperial Army/Captain Smith/Captain Smith Body/assets/paths.json
        .../Imperial Army/Captain Smith/Captain Smith Uniform/assets/paths.json
      Export:
        .../Imperial Army/Captain Smith/Captain Smith Body.json
        .../Imperial Army/Captain Smith/Captain Smith Uniform.json
  A character with only one variant folder works the same way, so it
  doesn't end up with a redundant folder wrapping a single file:
      Source: .../Imperial Army/Major Green Armored/assets/paths.json
      Export: .../Imperial Army/Major Green Armored.json
  Because each file keeps its own place in the tree, name clashes
  between similarly-named folders (e.g. two different "Officer"
  folders under different parents) simply don't happen in this mode -
  each ends up in its own correct subfolder.


FILES IN THIS FOLDER
---------------------
- TORC_to_Jedipedia_Converter.py   <- run this one
- converter.py                     <- the conversion logic (needed alongside
                                       the file above; don't delete it)
- README.txt                       <- this file


WHAT GETS CONVERTED, EXACTLY
------------------------------
- A "meta" block is added at the top of every output file:
    charType   -> always set to "unknown"
    charName   -> left blank
    nppPath    -> left blank (fill in by hand if needed)
    bodyType   -> auto-detected from model filenames when possible
                  (e.g. "bfn", "bmn"); left blank if it can't be
                  determined confidently
    errors     -> "TORC Conversion" plus any warnings from this run
- All numbers (color palettes, specular values, etc.) are converted to
  text strings, exactly as written in the source file.
- The order of fields inside each "otherValues" block is rearranged to
  match the Jedipedia format.
- Any "hair" slot missing a directionMap gets the standard default
  ("/art/defaultassets/black.dds") added automatically.
- Any eye material info missing a matPath gets the standard default
  ("/art/shaders/materials/eye_human_non_a01_c01.mat") added
  automatically, and a note is left in the file's errors list.
