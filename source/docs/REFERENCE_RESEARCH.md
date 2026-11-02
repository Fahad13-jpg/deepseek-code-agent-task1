# Reference research and implementation decisions

Reviewed on 29 October 2026. This research supports the desktop Code Agent requested in Task1-EN.docx. Repository code was inspected for mechanisms; no reference implementation was copied into this project.

## Corrected repository addresses

The document displays repository names without hyphens. Those exact URLs returned 404. Their matching public repositories are:

| Address in the task | Matching repository |
| --- | --- |
| ultraworkers/clawcode | https://github.com/ultraworkers/claw-code |
| Windy3f3f3f3f/howclaudecodeworks | https://github.com/Windy3f3f3f3f/how-claude-code-works |
| anthropics/claudecode | https://github.com/anthropics/claude-code |

The DOCX hyperlink targets are also truncated; the displayed names were used to identify these matching repositories.

## Claw Code

The inspected main tree resolved to commit `f4fff38de1d47a6aeafe5b6b279d3f15d7cdc712`. Its Rust runtime separates conversation orchestration, a tool-executor interface, permissions, session state, and streaming parsing. `conversation.rs` exposes iteration limits, usage reporting, interrupt/control signals, and event callbacks. `sse.rs` accumulates streamed data and dispatches complete events.

The Python `query_engine.py` examined in the same repository is a porting scaffold: its observed `submit_message` constructs summary text and estimated usage. It should not be mistaken for proof of an actual model request. `path_scope.py` and `permissions.py` show explicit workspace boundaries and permission decisions.

This implementation uses a smaller real API loop, typed tool definitions, UI events, iteration limits, interrupt checks, and scoped file tools. It assembles complete DeepSeek tool calls before execution, rather than executing partial streamed arguments.

Sources: [Rust conversation runtime](https://github.com/ultraworkers/claw-code/blob/f4fff38de1d47a6aeafe5b6b279d3f15d7cdc712/rust/crates/runtime/src/conversation.rs), [SSE parser](https://github.com/ultraworkers/claw-code/blob/f4fff38de1d47a6aeafe5b6b279d3f15d7cdc712/rust/crates/runtime/src/sse.rs), [Python query engine](https://github.com/ultraworkers/claw-code/blob/f4fff38de1d47a6aeafe5b6b279d3f15d7cdc712/src/query_engine.py), [path scope](https://github.com/ultraworkers/claw-code/blob/f4fff38de1d47a6aeafe5b6b279d3f15d7cdc712/src/path_scope.py).

## How Claude Code Works

The reference's agent-loop chapter describes a conversation layer around a repeated model/tool cycle. It separates lifecycle concerns such as usage and persistence from request execution, tool observations, and termination. It also describes context reduction and recovery in a much larger agent.

Here, `Agent` owns messages, usage, reports and completion gates; `DeepSeekClient` owns the HTTP stream; `Workspace` owns file operations. Tool failures return structured observations, allowing corrective model turns. A final text response triggers independent output checks. This implementation bounds context and stops with partial output rather than claiming to reproduce the reference's multi-stage compaction system.

Source: [Chapter 2, The Main Loop](https://github.com/Windy3f3f3f3f/how-claude-code-works/blob/main/en/docs/02-agent-loop.md). This is the repository author's analysis, not independently verified access to Anthropic's current implementation.

## Anthropic Claude Code

The public README describes agentic coding, codebase interaction, task execution, and integrations. It informed the intended user experience of a tool-using coding assistant. The inspected repository license states that use is subject to Anthropic's commercial terms; public availability does not make all of its contents an unrestricted open-source implementation. No proprietary implementation or prompt text is incorporated here.

Sources: [official repository README](https://github.com/anthropics/claude-code/blob/main/README.md), [license](https://github.com/anthropics/claude-code/blob/main/LICENSE.md).

## DeepSeek API contract

The official API documents list `deepseek-v4-pro` and `https://api.deepseek.com`. The app sends OpenAI-format chat messages and function-tool schemas to `/chat/completions`, with thinking enabled and SSE streaming. It reassembles fragmented tool arguments, pairs tool results with call IDs, records usage, and preserves every assistant `reasoning_content` field when replaying the in-memory conversation. DeepSeek documents that omitting this field during thinking/tool conversations can cause HTTP 400.

Transient HTTP failures are retried at most twice. Authentication and balance failures produce actionable errors. Dropped streams are not automatically replayed, and truncated tool calls are never executed. The model is fixed to V4 Pro; no fallback model is substituted.

Sources: [first API call](https://api-docs.deepseek.com/), [tool calling](https://api-docs.deepseek.com/guides/tool_calls/), [thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/), [chat completion contract](https://api-docs.deepseek.com/api/create-chat-completion/).

## Deliberate simplifications

This is a single-user desktop application with one model worker, sequential file tools, local JSON reports, and bounded context. It omits MCP, multiple agents, Git automation, general shell execution, cloud deployment, and persistent resumable sessions. Those mechanisms are unnecessary for the assignment's minimum inputs and outputs. The supplied Space Fractions microservices architecture describes the project to be generated, not a requirement to distribute the agent itself as microservices.

Qt provides native widgets; PyInstaller packages Python, Qt and dependencies into a Windows executable. The build includes a separate offline fixture solely for testing the packaged agent without credentials. Sources: [Qt deployment with PyInstaller](https://doc.qt.io/qtforpython-6/deployment/deployment-pyinstaller.html), [PyInstaller operating model](https://www.pyinstaller.org/en/stable/operating-mode.html).
