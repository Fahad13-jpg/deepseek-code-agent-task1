# DeepSeek Code Agent

A native Windows desktop application that turns architectural documentation and PlantUML views into a source-code project using the **official DeepSeek V4 Pro API**. It implements the code agent required by `Task1-EN.docx`. The supplied Space Fractions documents are example inputs to the agent.

## Run the desktop application

1. Double-click **DeepSeekCodeAgent.exe** in the submission folder. No Python installation, terminal, web browser, or local model download is needed.
2. Paste your DeepSeek API key. **Test connection** checks authentication and whether `deepseek-v4-pro` is listed for your account.
3. Use the supplied examples, or browse to your architecture and UML Markdown files. Click **Review inputs** to inspect the structured JSON and document inconsistencies.
4. Select an output folder and a project name. Add any preferences, such as the required technology stack, in **Additional instructions**.
5. For the Space Fractions demo, put this in **Additional instructions**: `Implement the game as a native desktop application with a graphical interface. Do not make a web app. Create a runnable main.py entry point and explain any required dependencies in README.md.`
6. Click **Generate project**. Follow the Activity tab. Inspect Project files and Report when it finishes, then click **Run generated game**. The launcher recognizes a root Windows executable, `main.py`/`game.py`/`app.py`, `index.html`/`game.html`, or a package with an npm `start`/`dev` script. Python and Node projects need those runtimes installed on the computer.

Windows x64 is the target. The executable was tested on Windows 11 x64. It is an unsigned local build, not an installer. The first launch may take several seconds while the bundled runtime is extracted to a temporary directory. Keep the supplied notices and source package with the executable when redistributing it.

Generation needs internet access, a valid API key, and sufficient DeepSeek balance. The application sends the two selected documents and your instructions to `https://api.deepseek.com/chat/completions`. API usage is billed to your account. There is no silent model substitution or third-party inference provider.

## What the agent does

The application parses the two input files into structured JSON, preserving the complete text, headings, code blocks, requirement identifiers, UML source, and input hashes. It sends that context to DeepSeek, receives tool calls, executes the allowed local tools, and returns the results to the model. The cycle repeats until output checks pass, the model finishes, the user stops it, or a configured limit is reached.

The model can create files, read generated files, replace a unique text section, search files, list the project, and request validation. Errors become tool observations so the model can repair its work. A plain-text claim of completion is rejected if mandatory output files or supported syntax checks are still failing.

The required generated deliverables are source files, a root README, a dependency manifest, and test cases. A Dockerfile is optional. The prompt requests setup/run/test instructions, an architecture mapping, and explicit assumptions. Their quality still depends on the model; structural validation does not prove architectural completeness or application correctness.

## Output layout

Each run creates a unique directory under the selected output folder:

```text
space-fractions-YYYYMMDD-HHMMSS-xxxxxx/
  README.md                     # Written by the model
  requirements.txt/package.json # Appropriate dependency manifest
  src/...                       # Full source; layout chosen by the model
  tests/...                     # Generated test cases
  .agent/
    inputs.json                 # Structured input and SHA-256 hashes
    events.jsonl                # Timestamped visible events and tool names
    conversation.json           # Public messages/tool calls; reasoning omitted
    report.json                 # Status, checks, usage and file hashes
    SUMMARY.md                  # Generation result and validation limits
    python-tests.log            # When optional Python tests are run
    child-tests.log             # Test output in the packaged Windows build
```

`completed` means the model finished and required-file/Python/JSON checks passed. `incomplete`, `cancelled`, and `failed` preserve partial output. Generation does not overwrite an existing project. The tool has no delete command, shell command, package installation, or unrestricted filesystem browsing tool.

## Validation and optional execution

Automatic checks verify nonempty required deliverables, parse generated Python with `ast.parse`, and parse JSON. JavaScript, TypeScript, C#, SQL, YAML and other languages are not compiled or executed by these checks.

**Allow generated Python tests to run** is off by default. When enabled, the agent can run `tests/test_*.py` with Python's `unittest` in a separate process using the bundled runtime. The child has a filtered environment and a 60-second timeout; zero discovered tests is a failure. The app does not install third-party dependencies. The frozen runtime contains the modules needed by this application and the fixture; it is not a complete Python development distribution.

Generated tests run with the Windows user's permissions and are **not sandboxed**. Enable execution only for code you are comfortable running. Tests that need additional dependencies, other runtimes, databases, or Docker must be run separately according to the generated README. Review the generated project before deployment.

## Credentials and limits

The key is held in memory by default. **Remember on this PC** encrypts it with Windows DPAPI under the current Windows user's account. Preferences live in `%LOCALAPPDATA%\DeepSeekCodeAgent\settings.json`. Uncheck Remember and close the app to remove the stored key. API keys are not put into prompts; exact-key redaction also protects stored logs. DeepSeek reasoning is retained in memory for correct tool-call replay but is not shown in the GUI or saved in the transcript.

Limits: 512 KB per input, 256 KB per generated file, 300 project files, 12 MB project contents, 2,000,000 conversation characters, and 5–120 model turns (100 by default). The accumulated-token budget is configurable from 100,000 to 2,000,000 (1,000,000 by default) and is checked between requests, so the final request can exceed it. Token counts use API usage reports and are not a currency spending cap. Maximum response size is 8 MB. Each request permits up to 32,768 generated tokens, and oversized model responses are retried with a smaller file batch.

Stop is cooperative. It stops before the next tool action and checks each streamed line; a stalled network read can take up to 60 seconds to time out. Closing the window during a run requests cancellation and closes when the worker finishes. Saved conversations are audit records, not resumable sessions. Start a fresh run after an interrupted request.

## Develop and rebuild

Developers need Windows x64 and Python 3.12 or later. The released executable does not require Python.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -I -m PyInstaller --noconfirm --clean DeepSeekCodeAgent.spec
```

Alternatively run `powershell -File .\build.ps1 -Python python`. The script installs dependencies, runs tests, builds `dist\DeepSeekCodeAgent.exe`, and runs the packaged self-test including real HTTPS transport initialization. The spec filters the build DLL search path so unrelated developer utilities cannot supply incompatible runtime DLLs, and includes companion SSL policy resources required by the build's Python distribution. The included source and spec can be rebuilt against a compatible, modified Qt/PySide distribution.

## Offline package check

```powershell
.\DeepSeekCodeAgent.exe --self-test --output "C:\Temp\AgentSmokeTest"
```

This deliberately uses a deterministic fixture and makes **no API requests**. It first initializes the real HTTPS client to check certificate resources, then verifies preprocessing, the tool loop, output checks, and execution of three tiny fraction tests using the packaged runtime. It writes `self-test-result.json`. It is not a substitute for live DeepSeek testing and is never used by normal GUI generation.

Live acceptance test: launch the GUI, configure your key, test connection, select the bundled examples, and generate a project. Verify `.agent/report.json` names `deepseek-v4-pro`, review the generated architecture mapping, install its dependencies in an appropriate development environment, run its tests, and launch it using its README. The packaged HTTPS transport was verified automatically; authenticated access and a real generation still need to be checked with your key in the GUI.

When updating, close the application before replacing its executable, or extract the new version into a separate folder. Python modules are loaded from the executable as needed; replacing a running executable can cause a decompression error. Version 1.0.1 is distributed in its own folder to keep the running session intact.

## Source layout and documentation

```text
main.py                     Desktop and packaged test entrypoints
codeagent/
  ui.py                     Native Qt interface and worker thread
  inputs.py                 Markdown / PlantUML preprocessing
  client.py                 Official API transport and SSE assembly
  agent.py                  Iterative agent loop and completion checks
  workspace.py              Scoped file tools and static validation
  runner.py                 Optional generated unittest execution
  settings.py               Preferences and Windows DPAPI
  selftest.py               Clearly labelled offline packaging fixture
tests/                      Automated unit, integration and GUI tests
examples/                   Original supplied Markdown inputs
docs/REFERENCE_RESEARCH.md  Repository research and implementation mapping
docs/INPUT_REVIEW.md        Findings in the supplied documents
docs/TASK_TRACEABILITY.md   Assignment-to-implementation mapping
docs/VERIFICATION.md        Actual verification and remaining live check
assets/                    Icon and Windows executable version metadata
licenses/                  Third-party license notices
```

This project is an independent implementation. It is not an Anthropic or DeepSeek product. See `THIRD_PARTY_NOTICES.md` for dependency and reference information.
