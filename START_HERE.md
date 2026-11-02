# Task 1 desktop submission - version 1.0.1

Double-click **DeepSeekCodeAgent.exe** to open the native Windows application. No Python installation or command line is required.

1. Enter your official DeepSeek API key and click **Test connection**.
2. The supplied architecture and UML example files are selected automatically. Click **Review inputs**.
3. Choose an output folder, set the project name, and add any preferences.
4. Click **Generate project**. Inspect the Activity, Project files and Report tabs.

Generation uses **deepseek-v4-pro** through DeepSeek's official API and incurs usage charges on your account. No API key is included in this submission.

The package contains:

- `DeepSeekCodeAgent.exe` â€” self-contained Windows x64 desktop application.
- `source/` â€” complete application source, dependency manifests, tests and rebuild script.
- `source/README.md` â€” setup, usage, architecture, limits and troubleshooting details.
- `source/docs/REFERENCE_RESEARCH.md` â€” research on all three task references.
- `source/docs/INPUT_REVIEW.md` â€” findings from the two supplied input documents.
- `source/docs/TASK_TRACEABILITY.md` â€” requirement coverage.
- `source/docs/VERIFICATION.md` â€” verification details and remaining live acceptance check.
- `source/examples/` â€” original architecture and UML inputs, also embedded in the executable.
- `references/Task1-EN.docx` â€” original assignment.
- `VERIFICATION.json`, `SHA256SUMS.txt` â€” test summary and executable checksum.
- `licenses/`, `THIRD_PARTY_NOTICES.md` â€” dependency notices.

Verified: **55 automated tests passed**, the actual desktop executable opened correctly, and the packaged offline test passed all three Python test cases with Python removed from PATH. The offline fixture is only a packaging check. A real DeepSeek generation still needs your API key and was not performed during delivery.

The referenced inputs mention a separate Requirements document that was not provided. The app also highlights conflicting uptime figures and an admin-component mismatch so the generated README can document assumptions.

Version 1.0.1 fixes the missing SSL certificate-policy resource that caused an Errno 2 error before API connection. The packaged HTTPS transport is now checked by the build self-test. A verified HTTPS diagnostic request reached DeepSeek and received the expected HTTP 401 for a deliberately invalid test key.

Updating: close the old application and launch the executable from this versioned folder. Do not replace an executable while it is running.
