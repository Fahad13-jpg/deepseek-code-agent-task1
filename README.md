# DeepSeek Code Agent — Task 1

A Windows desktop application that uses architecture documentation and UML/PlantUML views as input to a tool-using code agent. It sends requests to DeepSeek using the `deepseek-v4-pro` model identifier and writes generated projects into a user-selected output folder.

> This repository contains the code-generation application. The included Space Fractions documents are example inputs; the application is not itself the Space Fractions game.

> **Update note:** The source default token budget is now 1,000,000. The bundled `DeepSeekCodeAgent.exe` has not been rebuilt in this update and still uses the original 500,000-token default. To use the higher limit, rebuild the executable from `source/` on Windows using the instructions below.

## Run the Windows application

Download or clone this repository on Windows x64, then double-click `DeepSeekCodeAgent.exe` in the repository folder. No separate Python installation is required to run the packaged app.

1. Enter your DeepSeek API key in the app. The key is not included in this repository.
2. Click **Test connection**.
3. Review the supplied architecture and UML examples, or choose your own Markdown/text files.
4. Choose an output folder and project name, then click **Generate project**.
5. Review the generated files and report before using the generated software.

API usage is billed to the account associated with the key. The app reports token usage, but its token budget is not a dollar spending cap. Check current DeepSeek pricing and account limits before generation. The app requests the `deepseek-v4-pro` model identifier; provider routing and pricing policies may change.

## Source and development

The complete Python source, tests, build files, examples, and detailed documentation are in [`source/`](source/). Start with [`source/README.md`](source/README.md).

To run from source on Windows with Python 3.12 or later:

```powershell
cd source
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe main.py
```

To build the Windows executable, run from `source/`:

```powershell
powershell -File .\build.ps1 -Python python
```

## Verification notes

The included verification record reports 55 automated tests passed and a packaged offline self-test. The offline fixture makes no DeepSeek generation request and is not the Space Fractions game. A real authenticated generation and testing of a model-generated game are not claimed as verified in that record. See [`source/docs/VERIFICATION.md`](source/docs/VERIFICATION.md) for details and limitations.

## Repository map

- `DeepSeekCodeAgent.exe` — packaged Windows x64 application.
- `source/codeagent/` — UI, input preparation, API client, agent loop, workspace tools, settings, and test runner.
- `source/tests/` — automated tests for the application.
- `source/examples/` — supplied architecture and UML example inputs.
- `source/docs/` — research, input review, requirement traceability, and verification.
- `references/Task1-EN.docx` — original assignment brief.

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and `licenses/` for notices.

