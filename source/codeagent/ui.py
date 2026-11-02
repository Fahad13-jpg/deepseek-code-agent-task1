"""Native Qt desktop interface. API work always runs off the GUI thread."""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QIcon, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QScrollArea, QSpinBox, QSplitter, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from . import __version__
from .agent import Agent, RunConfig
from .client import DeepSeekClient, MODEL
from .inputs import preprocess
from .settings import load_settings, save_settings
from .workspace import Workspace


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


STYLE = """
QWidget { font-family: 'Segoe UI'; font-size: 13px; color: #202c43; }
QMainWindow, QWidget#main { background: #f3f5f9; }
QFrame#sidebar, QWidget#sideBody { background: #121c30; color: #eaf0ff; }
QFrame#sidebar QLabel, QFrame#sidebar QCheckBox { color: #d3dcec; }
QFrame#sidebar QLabel#brand { color: white; font-size: 21px; font-weight: 700; }
QFrame#sidebar QLabel#eyebrow { color: #8495b3; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QFrame#sidebar QLabel#section { color: #8eabff; font-size: 11px; font-weight: 700; }
QFrame#sidebar QLineEdit, QFrame#sidebar QSpinBox, QFrame#sidebar QPlainTextEdit {
 background: #1c2941; border: 1px solid #31415c; border-radius: 6px; padding: 8px; color: white; selection-background-color: #415ced;
}
QFrame#sidebar QPushButton { background: #263650; border: 1px solid #3b4d6b; color: white; }
QFrame#sidebar QPushButton:hover { background: #354765; }
QFrame#sidebar QCheckBox { font-size: 11px; }
QLabel#title { font-size: 28px; font-weight: 650; color: #18243b; }
QLabel#subtitle { color: #738098; font-size: 13px; }
QLabel#badge { background: #e7edff; color: #3654b5; padding: 8px 12px; border-radius: 6px; font-size: 11px; font-weight: 600; }
QLabel#metric { font-size: 23px; font-weight: 600; }
QLabel#metricLabel { font-size: 10px; font-weight: 650; color: #7a8597; }
QFrame#metricBox { background: white; border: 1px solid #e1e6ef; border-radius: 8px; }
QPushButton { padding: 8px 14px; border: 1px solid #d8dfea; background: white; border-radius: 6px; font-weight: 600; }
QPushButton:hover { border-color: #9aa9c6; background: #f3f6fc; }
QPushButton:disabled { color: #8994a6; background: #e8ecf3; border-color: #e0e5ee; }
QPushButton#primary, QFrame#sidebar QPushButton#primary { background: #4566f4; border: none; color: white; padding: 12px 14px; }
QPushButton#primary:hover { background: #3455e4; }
QPushButton#primary:disabled { background: #536381; color: #bbc5d6; }
QPushButton#stop { color: #b84444; }
QPlainTextEdit { background: white; border: 1px solid #e0e5ef; border-radius: 6px; padding: 16px; selection-background-color: #dce5ff; }
QTabWidget::pane { background: white; border: 1px solid #dfe5ef; border-radius: 7px; }
QTabBar::tab { padding: 13px 20px; background: transparent; color: #7a859b; font-weight: 600; }
QTabBar::tab:selected { color: #3559dc; border-bottom: 3px solid #4566f4; }
QTabBar::tab:hover { color: #3559dc; }
QProgressBar { border: none; background: #e0e6f0; max-height: 4px; border-radius: 2px; }
QProgressBar::chunk { background: #4566f4; }
QTreeWidget { border: none; background: #f8faff; padding: 10px; }
QTreeWidget::item { padding: 6px; }
QTreeWidget::item:selected { background: #dce6ff; color: #2442aa; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { width: 8px; background: transparent; }
QScrollBar::handle:vertical { background: #a0abc0; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QSplitter::handle { background: #e0e5ef; }
"""


class Worker(QThread):
    update = Signal(object)
    result = Signal(object)

    def __init__(self, key, config=None, inputs=None):
        super().__init__()
        self.key, self.config, self.inputs = key, config, inputs
        self.cancel = threading.Event()

    def run(self):
        client = None
        try:
            client = DeepSeekClient(self.key, self.cancel)
            if self.config is None:
                self.result.emit({"connection": client.verify()})
            else:
                self.result.emit(Agent(client, self.config, self.inputs, self.update.emit, self.cancel).run())
        except Exception as exc:
            message = str(exc).replace(self.key, "[REDACTED]") if self.key else str(exc)
            self.result.emit({"status": "failed", "summary": message})
        finally:
            self.key = ""
            if client:
                client.close()


class MainWindow(QMainWindow):
    def __init__(self, persist=True):
        super().__init__()
        self.persist = persist
        self.worker = None
        self.project_root = None
        self.close_requested = False
        self.stream_active = False
        self.preferences = load_settings() if persist else {}
        self.setWindowTitle("DeepSeek Code Agent")
        self.resize(1280, 860)
        self.setMinimumSize(1020, 700)
        self.setWindowIcon(QIcon(str(resource_root() / "assets" / "app.ico")))
        self.setStyleSheet(STYLE)
        container = QWidget(objectName="main")
        self.setCentralWidget(container)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame(objectName="sidebar")
        sidebar.setFixedWidth(350)
        outer = QVBoxLayout(sidebar)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget(objectName="sideBody")
        scroll.setWidget(body)
        side = QVBoxLayout(body)
        side.setContentsMargins(26, 28, 26, 24)
        side.setSpacing(10)
        side.addWidget(QLabel("DEEPSEEK", objectName="eyebrow"))
        side.addWidget(QLabel("Code Agent", objectName="brand"))
        tagline = QLabel("Turn architecture documents into\na complete source project.")
        tagline.setStyleSheet("color: #97a8c5; font-size: 12px;")
        side.addWidget(tagline)
        side.addSpacing(16)
        side.addWidget(QLabel("01   CONNECT", objectName="section"))
        side.addWidget(QLabel("DeepSeek API key"))
        self.key = QLineEdit(self.preferences.get("api_key", ""))
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("Paste your API key")
        self.key.setAccessibleName("DeepSeek API key")
        side.addWidget(self.key)
        keyrow = QHBoxLayout()
        self.show_key = QCheckBox("Show")
        self.show_key.toggled.connect(lambda show: self.key.setEchoMode(QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password))
        self.remember = QCheckBox("Remember on this PC")
        self.remember.setChecked(bool(self.preferences.get("api_key")))
        self.remember.setToolTip("Encrypts the key with Windows DPAPI for this Windows user.")
        keyrow.addWidget(self.show_key)
        keyrow.addWidget(self.remember)
        side.addLayout(keyrow)
        self.verify = QPushButton("Test connection")
        self.verify.clicked.connect(self.verify_connection)
        side.addWidget(self.verify)
        self.connection = QLabel("Official API · deepseek-v4-pro")
        self.connection.setWordWrap(True)
        self.connection.setStyleSheet("color: #8fa3c4; font-size: 11px;")
        side.addWidget(self.connection)
        side.addSpacing(16)
        side.addWidget(QLabel("02   SELECT INPUTS", objectName="section"))
        self.arch = self.path_row(side, "Architectural documentation", "architecture", False)
        self.views = self.path_row(side, "UML views", "views", False)
        samples = QPushButton("Use supplied example files")
        samples.clicked.connect(self.load_examples)
        side.addWidget(samples)
        self.input_controls = [samples, self.arch, self.views]
        side.addSpacing(16)
        side.addWidget(QLabel("03   CREATE PROJECT", objectName="section"))
        self.destination = self.path_row(side, "Output folder", "output", True)
        side.addWidget(QLabel("Project name"))
        self.project_name = QLineEdit("space-fractions")
        self.project_name.setAccessibleName("Project name")
        side.addWidget(self.project_name)
        side.addWidget(QLabel("Additional instructions  ·  optional"))
        self.instructions = QPlainTextEdit()
        self.instructions.setPlaceholderText("Preferred stack, scope, or constraints…")
        self.instructions.setFixedHeight(75)
        self.instructions.setAccessibleName("Additional instructions")
        side.addWidget(self.instructions)
        limits = QHBoxLayout()
        limits.addWidget(QLabel("Max model turns"))
        self.turns = QSpinBox()
        self.turns.setRange(5, 120)
        self.turns.setValue(50)
        self.turns.setAccessibleName("Maximum model turns")
        limits.addWidget(self.turns)
        side.addLayout(limits)
        self.execute = QCheckBox("Allow generated Python tests to run")
        self.execute.setToolTip("Runs generated Python code with your Windows user permissions. Not a sandbox. Optional, off by default.")
        side.addWidget(self.execute)
        note = QLabel("Optional test execution is unsandboxed.\nDefault checks do not execute generated code.")
        note.setStyleSheet("font-size: 10px; color: #93a3be;")
        side.addWidget(note)
        side.addStretch()
        outer.addWidget(scroll)
        layout.addWidget(sidebar)

        right = QWidget()
        main = QVBoxLayout(right)
        main.setContentsMargins(32, 28, 32, 24)
        main.setSpacing(18)
        header = QHBoxLayout()
        title = QVBoxLayout()
        title.addWidget(QLabel("Build from architecture", objectName="title"))
        title.addWidget(QLabel("Review your inputs, then let the agent implement and check the project.", objectName="subtitle"))
        header.addLayout(title)
        header.addStretch()
        about = QPushButton("Guide")
        about.clicked.connect(self.guide)
        header.addWidget(about)
        main.addLayout(header)
        badge = QLabel("DEEPSEEK V4 PRO     /     NATIVE WINDOWS APP", objectName="badge")
        badge.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main.addWidget(badge)
        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.state_metric = self.metric(metrics, "STATUS", "Ready")
        self.turn_metric = self.metric(metrics, "MODEL TURNS", "—")
        self.files_metric = self.metric(metrics, "PROJECT FILES", "0")
        self.tokens_metric = self.metric(metrics, "TOTAL TOKENS", "0")
        main.addLayout(metrics)
        self.tabs = QTabWidget()
        self.activity = self.editor()
        self.activity.setPlainText("YOUR NEXT PROJECT STARTS HERE\n\n1  Add your DeepSeek API key on the left.\n2  Select the architecture and UML Markdown files.\n3  Choose an output folder and review the inputs.\n4  Click Generate project.\n\nThe agent plans, writes files, checks its work, and repairs issues.\nEvery run gets a new folder, with source files and a generation report.\n\nYour selected documents are sent to DeepSeek when you generate.\nAPI usage is billed to your DeepSeek account.")
        self.tabs.addTab(self.activity, "Activity")
        self.input_preview = self.editor()
        self.tabs.addTab(self.input_preview, "Input review")
        filepane = QSplitter()
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderHidden(True)
        self.file_tree.setMinimumWidth(200)
        self.file_tree.itemClicked.connect(self.read_file)
        self.file_preview = self.editor(monospace=True)
        filepane.addWidget(self.file_tree)
        filepane.addWidget(self.file_preview)
        filepane.setSizes([230, 450])
        self.tabs.addTab(filepane, "Project files")
        self.report = self.editor()
        self.report.setPlainText("The generation report will appear here.\n\nIt records required deliverables, supported syntax checks, test execution results, and token usage.")
        self.tabs.addTab(self.report, "Report")
        main.addWidget(self.tabs, 1)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        main.addWidget(self.progress)
        self.status = QLabel("Ready. Review the supplied inputs or choose your own.", objectName="subtitle")
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        actions = QHBoxLayout()
        self.review = QPushButton("Review inputs")
        self.review.clicked.connect(lambda: self.review_inputs())
        actions.addWidget(self.review)
        self.open_folder = QPushButton("Open output folder")
        self.open_folder.setEnabled(False)
        self.open_folder.clicked.connect(self.open_output)
        actions.addWidget(self.open_folder)
        actions.addStretch()
        self.stop = QPushButton("Stop", objectName="stop")
        self.stop.setEnabled(False)
        self.stop.clicked.connect(self.stop_run)
        actions.addWidget(self.stop)
        self.start = QPushButton("Generate project  →", objectName="primary")
        self.start.clicked.connect(self.start_run)
        actions.addWidget(self.start)
        main.addLayout(actions)
        layout.addWidget(right, 1)
        for entry, setting, filename in [(self.arch, "architecture", "Architecture_Documentation.md"),
                                         (self.views, "views", "Architecture_View.md")]:
            saved = self.preferences.get(setting)
            entry.setText(str(resource_root() / "examples" / filename) if not saved or saved == "@example" else saved)
        self.destination.setText(self.preferences.get("output", str(Path.home() / "Documents" / "DeepSeek Projects")))
        self.review_inputs(switch=False)

    def path_row(self, layout, label, key, directory):
        layout.addWidget(QLabel(label))
        row = QHBoxLayout()
        entry = QLineEdit()
        entry.setAccessibleName(label)
        entry.textChanged.connect(entry.setToolTip)
        row.addWidget(entry, 1)
        button = QPushButton("…")
        button.setFixedWidth(36)
        button.setAccessibleName(f"Browse {label}")
        button.clicked.connect(lambda: self.browse(entry, directory))
        row.addWidget(button)
        layout.addLayout(row)
        return entry

    @staticmethod
    def editor(monospace=False):
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        if monospace:
            editor.setFont(QFont("Cascadia Code", 10))
            editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        return editor

    @staticmethod
    def metric(layout, label, value):
        box = QFrame(objectName="metricBox")
        column = QVBoxLayout(box)
        column.setContentsMargins(18, 14, 18, 14)
        column.addWidget(QLabel(label, objectName="metricLabel"))
        item = QLabel(value, objectName="metric")
        column.addWidget(item)
        layout.addWidget(box, 1)
        return item

    def browse(self, entry, directory):
        if self.worker:
            return
        path = QFileDialog.getExistingDirectory(self, "Select output folder", entry.text()) if directory else QFileDialog.getOpenFileName(self, "Select Markdown input", entry.text(), "Markdown and text (*.md *.markdown *.txt)")[0]
        if path:
            entry.setText(path)

    def load_examples(self):
        self.arch.setText(str(resource_root() / "examples" / "Architecture_Documentation.md"))
        self.views.setText(str(resource_root() / "examples" / "Architecture_View.md"))
        self.review_inputs()

    def review_inputs(self, switch=True):
        try:
            data = preprocess(Path(self.arch.text()), Path(self.views.text()))
            lines = ["INPUT REVIEW", "", f"Architecture: {data['architecture']['filename']}",
                     f"Views: {data['views']['filename']}",
                     f"{len(data['architecture']['sections'])} architecture headings · {len(data['diagrams'])} UML diagrams",
                     "Requirement IDs: " + ", ".join(data['architecture']['requirement_ids']), "", "Items to resolve during generation:"]
            lines.extend("• " + w for w in data["warnings"])
            lines.extend(["", "UML diagrams:", *["• " + d["name"] for d in data["diagrams"]], "", "STRUCTURED INPUT JSON", "", json.dumps(data, indent=2, ensure_ascii=False)])
            self.input_preview.setPlainText("\n".join(lines))
            if switch:
                self.tabs.setCurrentIndex(1)
                self.status.setText("Inputs are readable. Review assumptions above before generating.")
            return data
        except (OSError, ValueError) as exc:
            self.input_preview.setPlainText(str(exc))
            self.status.setText(str(exc))
            if switch:
                self.tabs.setCurrentIndex(1)
            return None

    def save_preferences(self):
        if self.persist:
            def selected(entry):
                path = Path(entry.text())
                return "@example" if path.is_file() and path.resolve().is_relative_to(resource_root() / "examples") else entry.text()
            save_settings({"architecture": selected(self.arch), "views": selected(self.views), "output": self.destination.text()}, self.key.text().strip(), self.remember.isChecked())

    def verify_connection(self):
        if self.worker:
            return
        if not self.key.text().strip():
            self.connection.setText("Enter an API key first.")
            return
        self.connection.setText("Checking the official API…")
        self.launch(Worker(self.key.text().strip()))

    def start_run(self):
        if self.worker:
            return
        if not self.key.text().strip():
            self.status.setText("Enter your DeepSeek API key before generating.")
            self.key.setFocus()
            return
        data = self.review_inputs(switch=False)
        if data is None:
            self.tabs.setCurrentIndex(1)
            return
        if not self.destination.text().strip():
            self.status.setText("Choose an output folder.")
            return
        if len(self.instructions.toPlainText()) > 10000:
            self.status.setText("Keep additional instructions under 10,000 characters.")
            return
        try:
            self.save_preferences()
        except OSError as exc:
            self.status.setText(f"Could not save preferences: {exc}")
            return
        config = RunConfig(Path(self.destination.text()), self.project_name.text().strip(),
                           self.instructions.toPlainText(), self.turns.value(), execute_tests=self.execute.isChecked())
        self.activity.clear()
        self.report.clear()
        self.file_tree.clear()
        self.file_preview.clear()
        self.project_root = None
        self.open_folder.setEnabled(False)
        self.stream_active = False
        self.turn_metric.setText("0")
        self.files_metric.setText("0")
        self.tokens_metric.setText("0")
        self.tabs.setCurrentIndex(0)
        self.launch(Worker(self.key.text().strip(), config, data))

    def launch(self, worker):
        self.worker = worker
        worker.update.connect(self.on_event)
        worker.result.connect(self.on_result)
        worker.finished.connect(self.worker_finished)
        self.set_busy(True)
        worker.start()

    def set_busy(self, busy):
        for item in [self.start, self.review, self.verify, self.key, self.remember, self.execute,
                     self.project_name, self.instructions, self.turns, self.destination, *self.input_controls]:
            item.setEnabled(not busy)
        self.stop.setEnabled(busy)
        self.progress.setRange(0, 0 if busy else 1)
        if busy:
            self.state_metric.setText("Working")
            self.status.setText("Waiting for DeepSeek. You can stop at any time.")

    def stop_run(self):
        if self.worker:
            self.worker.cancel.set()
            self.stop.setEnabled(False)
            self.status.setText("Stopping… waiting for the current network read (up to 60 seconds).")

    def on_event(self, event):
        kind = event["kind"]
        if kind == "started":
            self.project_root = Path(event["root"])
            self.open_folder.setEnabled(True)
        elif kind == "usage":
            self.tokens_metric.setText(f"{sum(event['usage'].values()):,}")
            return
        elif kind == "turn":
            self.turn_metric.setText(str(event["turn"]))
            self.status.setText(event["text"] + " · planning, writing and checking")
        elif kind == "delta":
            if not self.stream_active:
                self.activity.appendPlainText("\nAgent\n")
                self.stream_active = True
            self.activity.moveCursor(QTextCursor.MoveOperation.End)
            self.activity.insertPlainText(event["text"])
            self.activity.ensureCursorVisible()
            return
        elif kind == "assistant":
            self.stream_active = False
            return
        elif kind == "tool":
            self.files_metric.setText(str(event.get("file_count", 0)))
            if event.get("tool") in {"write_file", "replace_text"}:
                self.refresh_files()
        elif kind == "finished":
            return
        self.activity.appendPlainText(f"\n{kind.upper()}  {event['text']}")

    def on_result(self, result):
        if "connection" in result:
            self.connection.setText(result["connection"])
            self.status.setText(result["connection"])
            self.state_metric.setText("Ready")
            try:
                self.save_preferences()
            except OSError as exc:
                self.status.setText(f"Connected, but preferences could not be saved: {exc}")
            return
        status = result.get("status", "failed")
        self.state_metric.setText({"completed": "Complete", "cancelled": "Stopped", "incomplete": "Partial", "failed": "Failed"}.get(status, status))
        self.status.setText(result.get("summary", "Finished.")[:350])
        if self.worker and self.worker.config is None:
            self.connection.setText(result.get("summary", "Connection failed."))
        self.report.setPlainText(json.dumps(result, indent=2, ensure_ascii=False))
        self.activity.appendPlainText("\n" + status.upper() + "\n" + result.get("summary", ""))
        self.refresh_files()

    def worker_finished(self):
        worker = self.worker
        self.worker = None
        self.set_busy(False)
        if worker:
            worker.deleteLater()
        if self.close_requested:
            self.close()

    def refresh_files(self):
        if not self.project_root:
            return
        try:
            files = Workspace(self.project_root).files()
            self.file_tree.clear()
            for path in files:
                self.file_tree.addTopLevelItem(QTreeWidgetItem([path]))
            self.files_metric.setText(str(len(files)))
        except (ValueError, OSError) as exc:
            self.status.setText(str(exc))

    def read_file(self, item):
        if self.project_root:
            try:
                self.file_preview.setPlainText(Workspace(self.project_root).read(item.text(0)))
            except (OSError, ValueError, UnicodeError) as exc:
                self.file_preview.setPlainText(str(exc))

    def open_output(self):
        if self.project_root:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.project_root)))

    def guide(self):
        QMessageBox.information(self, "DeepSeek Code Agent guide", f"DeepSeek Code Agent {__version__}\n\n"
            "1. Configure your official DeepSeek API key and test the connection.\n"
            "2. Choose the architecture and UML Markdown files; review the parsed inputs.\n"
            "3. Choose the output folder, project name, and any additional instructions.\n"
            "4. Generate. Inspect the files and report when the agent finishes.\n\n"
            "The official deepseek-v4-pro API is the only model used. Generation incurs API charges. "
            "Documents are sent to DeepSeek. The key stays in memory unless you choose encrypted Windows storage.\n\n"
            "Generated source is written into a new project folder. Supported static checks run automatically. "
            "Optional Python unittest execution uses the bundled runtime and runs with your user permissions. "
            "Other languages require their own runtime to run the generated project.\n\n"
            "Limits: 500,000 accumulated tokens (checked between calls), 300 files, 256 KB per file, "
            "12 MB per project. Stop preserves partial output; API cancellation may take up to 60 seconds.\n\n"
            "See README.md and docs/REFERENCE_RESEARCH.md in the source package for implementation and research notes.")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.close_requested = True
            self.stop_run()
            event.ignore()
        else:
            try:
                self.save_preferences()
            except OSError:
                pass
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DeepSeek Code Agent")
    app.setOrganizationName("DeepSeekCodeAgent")
    window = MainWindow()
    window.show()
    return app.exec()
