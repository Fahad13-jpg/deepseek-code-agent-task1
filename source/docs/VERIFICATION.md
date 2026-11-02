# Verification record

Verification date: 29 October 2026. Platform: Windows 11 x64, build 26200. Source runtime: Python 3.12.14. GUI: PySide6 6.12.0. Packager: PyInstaller 6.22.3. Application version: 1.0.1.

## Automated tests

`python -m pytest -q` completed with **55 passed**. Coverage includes:

- Preservation and parsing of the actual supplied Markdown files, all 13 UML blocks, requirement identifiers, warnings, and malformed input rejection.
- Scoped file writes, reads, replacements and searches; Windows drive/UNC/traversal/device-name rejection; symlink and hard-link rejection; size limits; new-directory isolation.
- Official API URL and model selection; fragmented SSE tool arguments; reasoning retention; matching tool-result IDs across real transport calls using HTTPX MockTransport; HTTP errors and truncated responses.
- Real HTTPS transport initialization without a network request, plus an actionable error if a required certificate resource is missing.
- Iterative generation, false-completion rejection, output checks, cancellation, token budget handling, and the default prohibition on generated-code execution.
- A separate Python unittest child process executing three fraction tests.
- Windows DPAPI encryption/decryption and removal of remembered credentials; malformed preference files.
- Native GUI input review, required API key, a worker-thread generation fixture, output-file display, and control restoration.

Tests use fixtures or mocked network transport. They make no paid model calls and do not validate the quality of DeepSeek-generated code.

## Packaged executable

The one-file Windows executable was built and tested directly:

1. Launched the actual executable and inspected its native window and accessible controls.
2. Used its Review inputs button to confirm the original example files and document warnings are available from bundled resources.
3. Ran `--self-test --output <test folder>` successfully. The agent wrote four fixture files, completed three model-shaped tool rounds, passed static output checks, and executed all three Python unittest cases through the same packaged executable.
4. Repeated the packaged self-test with PATH restricted to `C:\Windows\System32`; it exited 0 with successful output and Python tests. No external Python executable was invoked.
5. In version 1.0.1, the packaged self-test also initialized the real HTTPS transport. A separate request from the packaged executable to the official `/models` endpoint with a deliberately invalid diagnostic key returned the expected HTTP 401 over verified TLS. No user key was used for that diagnostic request.

An initial package failed because DLL discovery picked up an unrelated ICU DLL from a developer utility on PATH. The final build specification sanitizes DLL search locations. Both packaged self-tests above ran after that correction.

This was not a clean virtual-machine test. The packaged interpreter and self-launching test child were verified on the development machine, including with Python removed from PATH. Windows 10, ARM64 and older Windows versions were not separately tested.

## Version 1.0.1 correction

The first release's fixture and mocked API tests did not instantiate the real HTTPS transport. The user encountered `[Errno 2] No such file or directory` when configuring a key. This was reproduced in the packaged application: its Python distribution loads a companion CA-policy file while creating `SSLContext`, but that file was not bundled. The build now includes the policy file. Certificate validation and the policy remain enabled. The packaged self-test now checks actual transport initialization, and `build.ps1` runs that self-test before reporting success.

Replacing the executable while the first release was still running caused a second error: `Error -3 while decompressing data: incorrect header check`. PyInstaller reopens the executable to load Python modules using offsets read at startup. The original file was restored for that session, and the corrected build was placed in a separate versioned release folder. All 193 archive entries and 350 bundled Python modules in the corrected executable were successfully extracted and decoded. The self-test and verified HTTPS diagnostic were repeated from the final versioned release location. Future updates must not replace a running executable.

## Remaining live acceptance check

The transport reaches the official API, but account authentication, billing access and a real V4 Pro generation have not been verified. The user should test their key in the GUI and generate from the example inputs. Inspect the resulting README, manifests, tests and architecture mapping, then run the generated project in the environment its dependencies require.

The test fixture is deliberately labelled offline. It is not a submitted Space Fractions implementation and is never substituted for the live model in normal GUI use. Project checks are structural and support Python/JSON syntax; they do not establish behavior, security, load capacity, production readiness or complete satisfaction of the input architecture.
