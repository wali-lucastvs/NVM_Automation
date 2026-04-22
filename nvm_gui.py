from __future__ import annotations

import logging
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from nvm_tool import (
    GenerationRequest,
    build_argument_parser,
    detect_input_type,
    format_cli_command,
    generate_artifacts,
)


class QueueLogHandler(logging.Handler):
    def __init__(self, message_queue: queue.Queue[str]) -> None:
        super().__init__()
        self.message_queue = message_queue

    def emit(self, record: logging.LogRecord) -> None:
        self.message_queue.put(self.format(record))


class NvMDesktopApp:
    OPERATIONS = {
        "generate_json": {
            "label": "Generate from JSON",
            "input_type": "json",
            "needs_previous": False,
            "allow_update": False,
        },
        "generate_excel": {
            "label": "Generate from Excel",
            "input_type": "excel",
            "needs_previous": False,
            "allow_update": False,
        },
        "merge_json": {
            "label": "Merge JSON + Previous ARXML",
            "input_type": "json",
            "needs_previous": True,
            "allow_update": False,
        },
        "merge_excel": {
            "label": "Merge Excel + Previous ARXML",
            "input_type": "excel",
            "needs_previous": True,
            "allow_update": False,
        },
        "update_json": {
            "label": "Update JSON + Previous ARXML",
            "input_type": "json",
            "needs_previous": True,
            "allow_update": True,
        },
        "update_excel": {
            "label": "Update Excel + Previous ARXML",
            "input_type": "excel",
            "needs_previous": True,
            "allow_update": True,
        },
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AUTOSAR NvM Automation Tool")
        self.root.geometry("980x760")
        self.root.minsize(900, 680)

        self.input_file_var = tk.StringVar()
        self.previous_arxml_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=str(Path("output").resolve()))
        self.verbose_var = tk.BooleanVar(value=False)
        self.command_preview_var = tk.StringVar(value="Select a command button to preview the equivalent CLI command.")
        self.detected_type_var = tk.StringVar(value="No input file selected")
        self.status_var = tk.StringVar(value="Ready")
        self.current_operation_key = "generate_json"
        self.message_queue: queue.Queue[str] = queue.Queue()
        self.worker_thread: threading.Thread | None = None

        self.input_file_var.trace_add("write", self._on_input_path_changed)
        self.previous_arxml_var.trace_add("write", self._on_form_field_changed)
        self.output_dir_var.trace_add("write", self._on_form_field_changed)
        self._configure_styles()
        self._build_layout()
        self._select_operation("generate_json", update_log=False)
        self.root.after(100, self._drain_log_queue)

    def _configure_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Header.TLabel", font=("Segoe UI Semibold", 18))
        style.configure("Subtle.TLabel", foreground="#4b5563")
        style.configure("Action.TButton", padding=(10, 8))

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(4, weight=1)

        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="AUTOSAR NvM Automation Tool", style="Header.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(
            header,
            text="Upload JSON or Excel, choose the README workflow, and generate output artifacts from a desktop app.",
            style="Subtle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        files_frame = ttk.LabelFrame(outer, text="Files", padding=12)
        files_frame.grid(row=1, column=0, sticky="ew", pady=(16, 12))
        files_frame.columnconfigure(1, weight=1)

        ttk.Label(files_frame, text="Input JSON/Excel").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=6)
        ttk.Entry(files_frame, textvariable=self.input_file_var).grid(row=0, column=1, sticky="ew", pady=6)
        ttk.Button(files_frame, text="Browse", command=self._browse_input).grid(row=0, column=2, sticky="ew", pady=6)

        ttk.Label(files_frame, text="Detected input").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=6)
        ttk.Label(files_frame, textvariable=self.detected_type_var).grid(row=1, column=1, sticky="w", pady=6)

        ttk.Label(files_frame, text="Previous NvM.arxml").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=6)
        ttk.Entry(files_frame, textvariable=self.previous_arxml_var).grid(row=2, column=1, sticky="ew", pady=6)
        ttk.Button(files_frame, text="Browse", command=self._browse_previous_arxml).grid(row=2, column=2, sticky="ew", pady=6)

        ttk.Label(files_frame, text="Output folder").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=6)
        ttk.Entry(files_frame, textvariable=self.output_dir_var).grid(row=3, column=1, sticky="ew", pady=6)
        ttk.Frame(files_frame).grid(row=3, column=2, sticky="ew")
        ttk.Button(files_frame, text="Browse", command=self._browse_output_dir).grid(row=3, column=2, sticky="ew", pady=6)

        options_frame = ttk.LabelFrame(outer, text="Options", padding=12)
        options_frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        options_frame.columnconfigure(2, weight=1)
        ttk.Checkbutton(
            options_frame,
            text="Verbose logging",
            variable=self.verbose_var,
            command=self._refresh_command_preview,
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            options_frame,
            text="Open Output Folder",
            style="Action.TButton",
            command=self._open_output_folder,
        ).grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Label(options_frame, textvariable=self.status_var, style="Subtle.TLabel").grid(
            row=0,
            column=2,
            sticky="e",
        )

        commands_frame = ttk.LabelFrame(outer, text="README Commands", padding=12)
        commands_frame.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        for column in range(3):
            commands_frame.columnconfigure(column, weight=1)

        operation_keys = list(self.OPERATIONS)
        for index, operation_key in enumerate(operation_keys):
            operation = self.OPERATIONS[operation_key]
            ttk.Button(
                commands_frame,
                text=operation["label"],
                style="Action.TButton",
                command=lambda key=operation_key: self._run_operation(key),
            ).grid(row=index // 3, column=index % 3, sticky="ew", padx=6, pady=6)

        ttk.Button(
            commands_frame,
            text="Show CLI Help",
            style="Action.TButton",
            command=self._show_help,
        ).grid(row=2, column=0, sticky="ew", padx=6, pady=6)
        ttk.Button(
            commands_frame,
            text="Clear Log",
            style="Action.TButton",
            command=self._clear_log,
        ).grid(row=2, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(
            commands_frame,
            text="Preview Current Command",
            style="Action.TButton",
            command=lambda: self._select_operation(self.current_operation_key),
        ).grid(row=2, column=2, sticky="ew", padx=6, pady=6)

        preview_frame = ttk.LabelFrame(outer, text="Command Preview", padding=12)
        preview_frame.grid(row=4, column=0, sticky="nsew")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(2, weight=1)
        ttk.Label(
            preview_frame,
            text="Equivalent CLI command for the selected workflow:",
            style="Subtle.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Entry(
            preview_frame,
            textvariable=self.command_preview_var,
            state="readonly",
        ).grid(row=1, column=0, sticky="ew", pady=(8, 12))

        log_frame = ttk.LabelFrame(preview_frame, text="Execution Log", padding=8)
        log_frame.grid(row=2, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, wrap="word", height=18, state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _on_input_path_changed(self, *_args: object) -> None:
        detected_type = detect_input_type(self.input_file_var.get().strip())
        self.detected_type_var.set(detected_type or "Unsupported file extension")
        self._refresh_command_preview()

    def _on_form_field_changed(self, *_args: object) -> None:
        self._refresh_command_preview()

    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Select JSON or Excel input",
            filetypes=[
                ("Supported files", "*.json *.xlsx *.xlsm"),
                ("JSON files", "*.json"),
                ("Excel files", "*.xlsx *.xlsm"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        self.input_file_var.set(path)

    def _browse_previous_arxml(self) -> None:
        path = filedialog.askopenfilename(
            title="Select previous NvM.arxml",
            filetypes=[("ARXML files", "*.arxml *.xml"), ("All files", "*.*")],
        )
        if not path:
            return
        self.previous_arxml_var.set(path)
        self._refresh_command_preview()

    def _browse_output_dir(self) -> None:
        path = filedialog.askdirectory(title="Select output folder")
        if not path:
            return
        self.output_dir_var.set(path)
        self._refresh_command_preview()

    def _show_help(self) -> None:
        self._append_log(build_argument_parser().format_help())
        self.status_var.set("CLI help shown in log")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")
        self.status_var.set("Log cleared")

    def _open_output_folder(self) -> None:
        output_dir = Path(self.output_dir_var.get()).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(output_dir)

    def _run_operation(self, operation_key: str) -> None:
        if self.worker_thread is not None and self.worker_thread.is_alive():
            messagebox.showinfo("NvM Automation Tool", "A generation job is already running.")
            return

        try:
            request = self._build_request(operation_key)
        except ValueError as exc:
            messagebox.showerror("NvM Automation Tool", str(exc))
            self.status_var.set("Validation failed")
            return

        self._select_operation(operation_key)
        self.status_var.set(f"Running: {self.OPERATIONS[operation_key]['label']}")
        self._append_log(f"Running {self.OPERATIONS[operation_key]['label']}")
        self._append_log(self.command_preview_var.get())

        self.worker_thread = threading.Thread(
            target=self._execute_request,
            args=(request,),
            daemon=True,
        )
        self.worker_thread.start()

    def _execute_request(self, request: GenerationRequest) -> None:
        handler = QueueLogHandler(self.message_queue)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        try:
            generated_files = generate_artifacts(request, log_handler=handler)
        except Exception as exc:  # noqa: BLE001
            self.message_queue.put(f"ERROR: {exc}")
            self.message_queue.put("__STATUS__:Generation failed")
            return

        self.message_queue.put("INFO: Generated files:")
        for file_path in generated_files:
            self.message_queue.put(f"INFO: {file_path}")
        self.message_queue.put("__STATUS__:Generation completed")

    def _build_request(self, operation_key: str) -> GenerationRequest:
        operation = self.OPERATIONS[operation_key]
        input_file = self.input_file_var.get().strip()
        if not input_file:
            raise ValueError("Select a JSON or Excel input file first.")

        detected_type = detect_input_type(input_file)
        if detected_type is None:
            raise ValueError("Input file must be .json, .xlsx, or .xlsm.")
        if detected_type != operation["input_type"]:
            raise ValueError(
                f"The selected command expects a {operation['input_type']} file, "
                f"but the chosen input looks like {detected_type}."
            )

        previous_arxml = self.previous_arxml_var.get().strip() or None
        if operation["needs_previous"] and previous_arxml is None:
            raise ValueError("This command requires a previous NvM.arxml file.")

        output_dir = self.output_dir_var.get().strip() or "output"
        return GenerationRequest(
            input_type=operation["input_type"],
            input_file=Path(input_file),
            previous_arxml=Path(previous_arxml) if previous_arxml else None,
            output_dir=Path(output_dir),
            verbose=self.verbose_var.get(),
            allow_update=operation["allow_update"],
        )

    def _select_operation(self, operation_key: str, update_log: bool = True) -> None:
        self.current_operation_key = operation_key
        self._refresh_command_preview()
        if update_log:
            self._append_log(f"Selected command: {self.OPERATIONS[operation_key]['label']}")

    def _refresh_command_preview(self) -> None:
        try:
            request = self._build_request(self.current_operation_key)
        except ValueError:
            operation = self.OPERATIONS[self.current_operation_key]
            preview = [
                "python",
                "generate_nvm.py",
                "--input-type",
                operation["input_type"],
                "--input-file",
                "<select file>",
                "--output",
                self.output_dir_var.get().strip() or "output",
            ]
            if operation["needs_previous"]:
                preview.extend(["--previous-arxml", "<select NvM.arxml>"])
            if operation["allow_update"]:
                preview.append("--allow-update")
            if self.verbose_var.get():
                preview.append("--verbose")
            self.command_preview_var.set(" ".join(preview))
            return

        self.command_preview_var.set(format_cli_command(request))

    def _drain_log_queue(self) -> None:
        while True:
            try:
                message = self.message_queue.get_nowait()
            except queue.Empty:
                break

            if message.startswith("__STATUS__:"):
                self.status_var.set(message.split(":", 1)[1])
            else:
                self._append_log(message)

        self.root.after(100, self._drain_log_queue)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, message.rstrip() + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")


def main() -> None:
    root = tk.Tk()
    NvMDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
