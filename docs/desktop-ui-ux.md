# LEGO AI Agent — Desktop UI/UX v1

**Status:** Design baseline for the existing local desktop web interface. UI refinements and the task-composer integration remain deferred.

## Product goals

- Make the agent task-first: help the user complete local work through safe, registered tools, not just produce chat text.
- Keep the interface simple, readable, and friendly for one person using a local agent.
- Make local-only operation visible: the UI is served by the local FastAPI process and uses same-origin, relative API URLs.
- Keep all inference on the configured local Ollama service. No cloud APIs, remote assets, analytics, or telemetry.
- Make tool actions understandable and approval-gated. The model never executes tools directly.
- Avoid arbitrary shell, Python, or filesystem actions. Only fixed registry tools may be displayed or dispatched.

## First-screen layout

1. **Top bar**
   - LEGO AI Agent name and version.
   - A visible `Local` indicator and backend status (`Checking`, `Online`, or `Offline`).
   - Status comes from `GET /health`; an offline status must not prevent the page from explaining how to restart the local backend.

2. **Left panel — Tools**
   - Load available entries from `GET /tools`.
   - Show each tool's name, short description, risk, and whether approval is required.
   - Selecting a tool opens a form based only on its returned JSON schema. Do not invent extra tool names or fields.

3. **Main panel — Tasks and results**
   - Center the user's requested task, a clear running/approval/completed state, and the result.
   - Keep conversational text as the way to describe a task and receive a concise result.
   - Separate model planning from execution; the model must not directly execute tools.
   - Do not render model output as HTML; insert it as text to avoid script injection.

4. **Task composer**
   - Multi-line request box and one clear action button.
   - Show local status and explain that task execution uses only the fixed tool registry.
   - Disable repeat submission while a task is in flight.
   - No attachment controls in the current build; media is deferred.

## Tool action and approval flow

1. The user selects a tool and fills fields from the registered JSON schema.
2. Before dispatch, show a review panel with the exact tool name, arguments, risk, and approval requirement.
3. For tools with `requires_approval: true`, the review must display the complete target path and complete text content. It has separate **Confirm and run** and **Cancel** actions. No dispatch request is sent before the user presses **Confirm and run**.
4. Only after that click may the UI send `POST /tools/dispatch` with `approved: true`. For tools that do not require approval, send `approved: false`.
5. Always display the structured result (`success`, `message`, and safe error); never claim an action succeeded unless the response says `success: true`.
6. Treat registry validation and approval as authoritative. A UI state, model message, or submitted argument must not bypass the backend gate.

## Visual and accessibility direction

- Calm, uncluttered, light neutral background with LEGO-inspired yellow used sparingly for the primary action and focus accents; avoid toy-like decoration.
- Strong contrast, readable type, clear separation between chat, tool controls, and approval review.
- Keyboard reachable controls, visible focus, labels tied to inputs, semantic headings, and status updates announced accessibly.
- On narrower windows, tools collapse into a drawer while the chat stays usable; approval review remains prominent and never becomes a hidden toast.
- No external fonts, scripts, image services, or other network-loaded assets in v1.

## Existing API contract used by v1

- `GET /health` — local backend status.
- `POST /chat` — one plain-text message and one reply; it does not execute tools.
- `POST /agent/task` — proposes one registered action, executes only actions whose registry metadata does not require approval, and returns approval-required actions without executing them. Multiple proposals are rejected for clarification.
- `GET /tools` — fixed registry schemas and safety metadata.
- `POST /tools/dispatch` — fixed registry dispatch; approval is false unless explicitly supplied.
- The task endpoint is implemented but is not yet connected to the frontend composer or an approval review UI.

All browser requests must use relative same-origin paths (`/health`, `/chat`, `/agent/task`, `/tools`, `/tools/dispatch`), not hard-coded `localhost` or `127.0.0.1` URLs.

## v1 acceptance criteria

- The page remains usable with the API offline and displays an honest connection status.
- A chat response is rendered as inert text, never HTML.
- Registered tool names and schemas are fetched from the backend rather than duplicated in frontend code.
- An approval-required action cannot be dispatched from the interface until the user confirms the exact displayed details.
- Cancel sends no dispatch request; successful execution is indicated only by a successful backend result.
- No cloud request, analytics, arbitrary command execution, or unregistered tool is introduced.
