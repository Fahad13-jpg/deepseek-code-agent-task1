# Third-party notices

The application is independently implemented and is not affiliated with DeepSeek, Anthropic, or Qt. The supplied task and example architecture documents retain their original ownership. Reference repositories were studied for mechanisms; their implementation code was not copied.

The executable bundles Python, PySide6/Shiboken/Qt and the HTTPX dependency stack. License notices are included in `licenses/`. PySide6 is offered under LGPLv3/GPL and commercial terms; this project uses the open-source distribution available from PyPI. Qt libraries are dynamically loaded. Full application source and a build specification are included so users can rebuild the application with compatible modified library versions. No restriction is imposed on reverse engineering needed to debug such modifications.

| Component | Project / source |
| --- | --- |
| Python 3.12 | https://www.python.org/ and https://github.com/python/cpython |
| PySide6 and Shiboken 6.12.0 | https://code.qt.io/cgit/pyside/pyside-setup.git/ |
| Qt 6.12.0 | https://code.qt.io/cgit/qt/ and https://download.qt.io/archive/qt/6.12/ |
| HTTPX / HTTPCore | https://github.com/encode/httpx and https://github.com/encode/httpcore |
| AnyIO | https://github.com/agronholm/anyio |
| certifi | https://github.com/certifi/python-certifi |
| h11 | https://github.com/python-hyper/h11 |
| idna | https://github.com/kjd/idna |
| typing_extensions | https://github.com/python/typing_extensions |
| PyInstaller bootloader | https://github.com/pyinstaller/pyinstaller |

PyInstaller's bootloader license includes an exception for distributing applications built with it. Qt and Python also include third-party components under their respective notices. See the upstream source distributions for full component inventories and build instructions.
