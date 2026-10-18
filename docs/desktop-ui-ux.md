# LEGO AI Agent — Desktop UI/UX v1

**Status:** Design baseline for the local desktop web interface. This document defines the first implementation scope; it does not add frontend code yet.

## Product goals

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

3. **Main panel — Chat**
   - Show user and assistant messages as plain text.
   - Send one message to `POST /chat` as `{ "message": "..." }` and display the returned `reply`.
   - Show a loading state while the local model responds and a plain, safe error if it is unavailable.
   - Do not render model output as HTML; insert it as text to avoid script injection.

4. **Composer**
   - Multi-line text box, send button, and a small note that messages go to the local model.
   - Enforce the backend's 4,000-character maximum before sending.
   - Disable repeat submission while a request is in flight.

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
- `POST /chat` — one plain-text message and one reply; no tool execution.
- `GET /tools` — fixed registry schemas and safety metadata.
- `POST /tools/dispatch` — fixed registry dispatch; approval is false unless explicitly supplied.

All browser requests must use relative same-origin paths (`/health`, `/chat`, `/tools`, `/tools/dispatch`), not hard-coded `localhost` or `127.0.0.1` URLs.

## v1 acceptance criteria

- The page remains usable with the API offline and displays an honest connection status.
- A chat response is rendered as inert text, never HTML.
- Registered tool names and schemas are fetched from the backend rather than duplicated in frontend code.
- An approval-required action cannot be dispatched from the interface until the user confirms the exact displayed details.
- Cancel sends no dispatch request; successful execution is indicated only by a successful backend result.
- No cloud request, analytics, arbitrary command execution, or unregistered tool is introduced.
