from __future__ import annotations

import logging
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from nvm_tool import NvMConfigParser
from nvm_tool.config import load_version_profile
from nvm_tool.generator import generate


class NvMVersionedApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("NvM Versioned Generator")
        self.input_file_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=str(Path("workspace/output").resolve()))
        self.status_var = tk.StringVar(value="Ready")
        self.autosar_version_var = tk.StringVar()
        self.message_queue: queue.Queue[str] = queue.Queue()
        self.worker_thread: threading.Thread | None = None

        self._build()
        self._load_versions()
        self.root.after(100, self._drain_queue)

    def _build(self):
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Input JSON/Excel").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.input_file_var, width=60).grid(row=0, column=1, sticky="ew")
        ttk.Button(frame, text="Browse", command=self._browse_input).grid(row=0, column=2)

        ttk.Label(frame, text="AUTOSAR Version").grid(row=1, column=0, sticky="w")
        self.version_combo = ttk.Combobox(frame, textvariable=self.autosar_version_var, state="readonly")
        self.version_combo.grid(row=1, column=1, sticky="ew")

        ttk.Label(frame, text="Output dir").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.output_dir_var).grid(row=2, column=1, sticky="ew")
        ttk.Button(frame, text="Generate", command=self._generate).grid(row=3, column=1)

        ttk.Label(frame, textvariable=self.status_var).grid(row=4, column=0, columnspan=3, sticky="w")

    def _load_versions(self):
        versions_root = Path(__file__).resolve().parent / "versions"
        if not versions_root.exists():
            versions_root = Path("versions")
        versions = [p.name for p in versions_root.iterdir() if p.is_dir() and (p / "config.yaml").exists()]
        self.version_combo['values'] = sorted(versions)
        if versions:
            self.autosar_version_var.set(sorted(versions)[0])

    def _browse_input(self):
        path = filedialog.askopenfilename(filetypes=[("Supported", "*.json *.xlsx *.xlsm"), ("All","*.*")])
        if path:
            self.input_file_var.set(path)

    def _generate(self):
        if self.worker_thread is not None and self.worker_thread.is_alive():
            messagebox.showinfo("NvM", "Generation already running")
            return

        input_file = self.input_file_var.get().strip()
        version_key = self.autosar_version_var.get().strip()
        output = Path(self.output_dir_var.get())
        if not input_file or not version_key:
            messagebox.showerror("NvM", "Select input file and AUTOSAR version")
            return

        self.status_var.set("Running")
        self.worker_thread = threading.Thread(target=self._worker, args=(input_file, version_key, output), daemon=True)
        self.worker_thread.start()

    def _worker(self, input_file, version_key, output):
        logger = logging.getLogger("nvm_gui_versioned")
        parser = NvMConfigParser(logger=logger)
        try:
            blocks = parser.parse_input_file("json" if input_file.endswith(".json") else "excel", input_file)
            profile = load_version_profile(version_key)
            out = generate(blocks, output, profile, logger=logger, versioned=True)
            self.message_queue.put(f"INFO: Generated {output / 'NvM_Cfg.h'}, {output / 'NvM_Cfg.c'}, {out}")
            self.message_queue.put("__STATUS__:Completed")
        except Exception as exc:
            self.message_queue.put(f"ERROR: {exc}")
            self.message_queue.put("__STATUS__:Failed")

    def _drain_queue(self):
        while True:
            try:
                msg = self.message_queue.get_nowait()
            except Exception:
                break
            if msg.startswith("__STATUS__:"):
                self.status_var.set(msg.split(":",1)[1])
            else:
                # append to status for simplicity
                self.status_var.set(msg)
        self.root.after(100, self._drain_queue)


def main():
    root = tk.Tk()
    NvMVersionedApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
