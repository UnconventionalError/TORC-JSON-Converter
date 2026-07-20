"""
TORC paths.json -> Jedipedia Converter
=======================================

A simple point-and-click tool. No installation needed beyond Python itself.

HOW TO RUN
----------
1. Make sure Python 3 is installed (python.org/downloads - the free installer
   includes everything this tool needs).
2. Double-click this file, OR open a terminal/command prompt in this folder
   and run:  python TORC_to_Jedipedia_Converter.py

HOW TO USE
----------
1. Click "Choose Source Folder..." and pick the top-level folder that
   contains your paths.json files (it will search every subfolder too).
2. Click "Choose Export Folder..." and pick where the converted .json
   files should be saved.
3. Click "Convert All".
4. Watch the log for progress. Any warnings/notes about a specific file
   are also written into that file's own meta.errors block, so you can
   always see them later just by opening the JSON.
"""

import json
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from converter import (
    assign_output_names,
    assign_output_paths_preserving_structure,
    convert_paths_json,
    find_paths_json_files,
)


class ConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TORC \u2192 Jedipedia paths.json Converter")
        self.root.geometry("760x560")
        self.root.minsize(620, 420)

        self.source_dir = tk.StringVar(value="(none selected)")
        self.export_dir = tk.StringVar(value="(none selected)")
        self.preserve_structure = tk.BooleanVar(value=False)
        self._source_path = None
        self._export_path = None

        self._log_queue = queue.Queue()

        self._build_widgets()
        self.root.after(100, self._poll_log_queue)

    # ------------------------------------------------------------------ UI

    def _build_widgets(self):
        pad = {"padx": 10, "pady": 6}

        top = ttk.Frame(self.root)
        top.pack(fill="x", **pad)

        ttk.Label(top, text="1. Source folder (searched recursively):").grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        ttk.Button(top, text="Choose Source Folder...", command=self.choose_source).grid(
            row=1, column=0, sticky="w"
        )
        ttk.Label(top, textvariable=self.source_dir, foreground="#333").grid(
            row=1, column=1, sticky="w", padx=8
        )

        ttk.Label(top, text="2. Export folder (all output files go here):").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(12, 0)
        )
        ttk.Button(top, text="Choose Export Folder...", command=self.choose_export).grid(
            row=3, column=0, sticky="w"
        )
        ttk.Label(top, textvariable=self.export_dir, foreground="#333").grid(
            row=3, column=1, sticky="w", padx=8
        )

        ttk.Checkbutton(
            top,
            text="Preserve source folder structure in export "
                 "(otherwise all files are saved flat into one folder)",
            variable=self.preserve_structure,
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))

        action = ttk.Frame(self.root)
        action.pack(fill="x", **pad)
        self.convert_btn = ttk.Button(
            action, text="3. Convert All", command=self.start_conversion
        )
        self.convert_btn.pack(side="left")

        self.open_export_btn = ttk.Button(
            action, text="Open Export Folder", command=self.open_export_folder, state="disabled"
        )
        self.open_export_btn.pack(side="left", padx=8)

        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=(0, 6))

        ttk.Label(self.root, text="Log:").pack(anchor="w", padx=10)
        self.log_box = scrolledtext.ScrolledText(self.root, wrap="word", state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # -------------------------------------------------------------- helpers

    def choose_source(self):
        chosen = filedialog.askdirectory(title="Select the folder to search for paths.json files")
        if chosen:
            self._source_path = Path(chosen)
            self.source_dir.set(chosen)

    def choose_export(self):
        chosen = filedialog.askdirectory(title="Select the export folder for Jedipedia .json files")
        if chosen:
            self._export_path = Path(chosen)
            self.export_dir.set(chosen)

    def open_export_folder(self):
        if not self._export_path:
            return
        import os
        import platform
        import subprocess

        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(str(self._export_path))  # noqa
            elif system == "Darwin":
                subprocess.run(["open", str(self._export_path)])
            else:
                subprocess.run(["xdg-open", str(self._export_path)])
        except Exception:
            pass

    def log(self, message):
        self._log_queue.put(message)

    def _poll_log_queue(self):
        try:
            while True:
                message = self._log_queue.get_nowait()
                self.log_box.configure(state="normal")
                self.log_box.insert("end", message + "\n")
                self.log_box.see("end")
                self.log_box.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log_queue)

    # --------------------------------------------------------------- logic

    def start_conversion(self):
        if not self._source_path or not self._source_path.is_dir():
            messagebox.showwarning("Missing source", "Please choose a valid source folder first.")
            return
        if not self._export_path:
            messagebox.showwarning("Missing export folder", "Please choose an export folder first.")
            return

        self._export_path.mkdir(parents=True, exist_ok=True)

        self.convert_btn.configure(state="disabled")
        self.open_export_btn.configure(state="disabled")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        thread = threading.Thread(target=self._run_conversion, daemon=True)
        thread.start()

    def _run_conversion(self):
        start_time = time.perf_counter()

        self.log(f"Searching for paths.json files under: {self._source_path}")
        found = find_paths_json_files(self._source_path)

        if not found:
            self.log("No paths.json files were found. Nothing to do.")
            self._finish()
            return

        self.log(f"Found {len(found)} file(s). Starting conversion...\n")

        if self.preserve_structure.get():
            self.log("Mode: preserving source folder structure.\n")
            pairs = assign_output_paths_preserving_structure(found, self._source_path)
        else:
            self.log("Mode: flat export (all files in one folder).\n")
            pairs = [
                (src, Path(name)) for src, name in assign_output_names(found)
            ]

        self.progress["maximum"] = len(pairs)
        self.progress["value"] = 0

        success_count = 0
        warning_count = 0

        for source_path, output_rel_path in pairs:
            self.log(f"Converting: {source_path}")
            try:
                assumed_name = output_rel_path.stem
                result = convert_paths_json(source_path, assumed_char_name=assumed_name)
                out_path = self._export_path / output_rel_path
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(result.data, f, indent=4)

                notes = [e for e in result.errors if e != "TORC Conversion"]
                if notes:
                    warning_count += 1
                    for note in notes:
                        self.log(f"    \u26a0 {note}")
                self.log(f"    \u2192 Saved as: {output_rel_path}")
                success_count += 1
            except Exception as exc:  # keep the batch going no matter what
                self.log(f"    \u2717 FAILED: {exc}")

            self.progress["value"] += 1

        self.log("")
        elapsed = time.perf_counter() - start_time
        self.log(f"Done. {success_count}/{len(pairs)} file(s) converted "
                  f"({warning_count} with notes/warnings).")
        self.log(f"Time taken: {self._format_elapsed(elapsed)}")
        self._finish()

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.2f} seconds"
        minutes, secs = divmod(seconds, 60)
        return f"{int(minutes)}m {secs:.1f}s"

    def _finish(self):
        self.convert_btn.configure(state="normal")
        self.open_export_btn.configure(state="normal")


def main():
    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
