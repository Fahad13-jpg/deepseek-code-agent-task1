import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase

from codeagent import ui
from codeagent.selftest import FixtureClient


APP = QApplication.instance() or QApplication([])
if os.name == "nt":
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")


def test_input_preview_and_required_key():
    window = ui.MainWindow(persist=False)
    window.show()
    APP.processEvents()
    assert "13 UML diagrams" in window.input_preview.toPlainText()
    QTest.mouseClick(window.review, Qt.MouseButton.LeftButton)
    assert window.tabs.currentIndex() == 1
    QTest.mouseClick(window.start, Qt.MouseButton.LeftButton)
    assert window.worker is None
    assert "API key" in window.status.text()
    window.close()


def test_gui_worker_generates_and_releases_controls(tmp_path, monkeypatch):
    class Client(FixtureClient):
        def __init__(self, *args):
            super().__init__()
        def close(self):
            pass
    monkeypatch.setattr(ui, "DeepSeekClient", Client)
    window = ui.MainWindow(persist=False)
    window.show()
    window.key.setText("test-only")
    window.destination.setText(str(tmp_path))
    window.start_run()
    assert not window.start.isEnabled()
    deadline = time.monotonic() + 10
    while window.worker and time.monotonic() < deadline:
        APP.processEvents()
        time.sleep(0.01)
    assert window.worker is None
    assert window.state_metric.text() == "Complete"
    assert window.start.isEnabled()
    assert window.file_tree.topLevelItemCount() == 4
    assert window.open_folder.isEnabled()
    window.close()
