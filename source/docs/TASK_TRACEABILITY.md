# Task requirement coverage

| Requirement from Task1-EN.docx | Implementation | Verification |
| --- | --- | --- |
| Research the provided Claude Code references | REFERENCE_RESEARCH.md with corrected addresses, source links and design mapping | Public repositories and relevant source files inspected |
| Implement a simplified Code Agent | agent.py iterative model/tool loop, observations, repair turns, output checks | Agent integration and protocol tests |
| Use official DeepSeek V4 Pro API | client.py fixes the endpoint and model to api.deepseek.com and deepseek-v4-pro | HTTP/SSE tests verify exact endpoint, model and reasoning replay; live call requires the user's key |
| No local model deployment | Remote API transport only | No weights or inference runtime included |
| Windows desktop executable | Native PySide6 GUI; PyInstaller one-file build | Packaged startup and offline smoke check |
| No preinstalled Python on target | Python interpreter, Qt and dependencies bundled | Frozen self-test invokes the same executable for Python tests |
| API-key configuration | Masked key field, Test connection, optional Windows DPAPI storage | GUI and encryption tests |
| Input-file selection | Independent file pickers for architecture and views | Input validation and GUI tests |
| Task triggering | Generate project button with worker thread, progress and Stop | GUI fixture and cancellation tests |
| Output-directory assignment | Output-folder picker and unique project subdirectory | Collision and path-scope tests |
| Structured preprocessing recommended | Full Markdown/PlantUML-to-JSON preprocessing | All 13 supplied UML blocks extracted |
| Source layout, full source files | Agent file tools, file browser and manifest hashes | Required-source completion gate |
| Dependency manifest | Completion gate checks common manifest names | Static validator tests |
| Project README | Root README.md completion gate | Missing output rejected |
| Test cases | Test-source detection and optional Python unittest tool | Missing test files rejected; offline fixture executes three cases |
| Optional Dockerfile | Model may generate one when appropriate | Not mandatory for desktop agent |

The desktop delivery satisfies the preferred form factor; the CLI-launched web fallback is not used. Structural output checks enforce the presence of deliverables, not their semantic completeness. Live quality and functionality of a generated project must be assessed after a real run.
