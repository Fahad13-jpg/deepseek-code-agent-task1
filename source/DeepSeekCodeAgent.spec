# Rebuild on Windows using Python 3.12+ and requirements-dev.txt.
from pathlib import Path
import os
import sys
import ssl
import PySide6
import shiboken6

# Do not collect unrelated DLLs from a developer's tools on PATH. Windows ships
# UCRT and ICU; an older Poppler/libheif ICU can shadow the system implementation.
os.environ['PATH'] = os.pathsep.join([
    str(Path(PySide6.__file__).parent), str(Path(shiboken6.__file__).parent),
    str(Path(sys.prefix) / 'Scripts'),
    str(Path(os.environ['SystemRoot']) / 'System32'), os.environ['SystemRoot'],
])

root = Path(SPECPATH)
runtime_data = [(str(root / 'examples'), 'examples'), (str(root / 'assets'), 'assets')]
# Some Python distributions load an extra CA policy file from ssl.py's directory
# when constructing SSLContext. Keep that policy in the frozen runtime as well.
# Never work around a missing policy file by disabling certificate verification.
ssl_policy = Path(ssl.__file__).parent / 'codex-rejected-cas.pem'
if ssl_policy.is_file():
    runtime_data.append((str(ssl_policy), '.'))
a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root)],
    binaries=[],
    datas=runtime_data,
    hiddenimports=['unittest', 'unittest.mock', 'fractions'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQml', 'PySide6.QtQuick', 'tkinter', 'pytest', 'pygments', 'httpx._main'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='DeepSeekCodeAgent', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False,
    disable_windowed_traceback=False,
    icon=str(root / 'assets' / 'app.ico'),
    version=str(root / 'assets' / 'version_info.txt'),
)
