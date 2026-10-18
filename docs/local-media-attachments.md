# Local Media Attachments — Implementation Plan

**Status:** Media attachments are paused. The PDF upload control and endpoint were removed after the live test failed. Do not re-add attachments until the task-execution workflow is working; keep the current UI appearance stable and defer visual polish until the end of the creation phase.

## Goals and boundaries

- Let the user deliberately attach local PDFs, images, and videos to a chat request.
- Keep parsing, inference, and any frame extraction on this computer. Do not send files to cloud services.
- Never accept arbitrary local paths from the browser. Receive only user-selected upload bytes through the local API.
- Do not persist uploaded content after the request. Use bounded in-memory processing where possible and clean temporary data if a decoder requires it.
- Treat document text, image content, and video frames as untrusted user data, not as instructions that can override the system prompt.
- Keep tool calls separate from attachment analysis. Reading an attachment must never execute a tool or write into the approved workspace.

## Rollout order

### 1. PDF text extraction

- Accept one user-selected PDF as the raw request body at `POST /chat/pdf`; send the question in the `X-Chat-Message` header and extract embedded text with the free local `pypdf` library.
- Enforce a 10 MiB upload limit, a 40-page limit, a 12,000-character extracted-text cap, and a 4,000-character question limit.
- Keep the original file in memory; do not save it to disk. Return a clear message when the PDF is encrypted, malformed, over a limit, or has no extractable text.
- Scanned/image-only PDFs are not OCR'd in this first PDF step. Add local OCR only after selecting and testing a zero-cost offline package/model.

### 2. Images

- Accept a small set of image formats and size limits, validate file signatures rather than trusting only the browser MIME type, and pass image bytes to Ollama in memory.
- Image understanding requires a vision-capable model. The installed `llama3.2:3b` is text-only, so this feature must not pretend that it can see images.
- Do not download or switch models automatically. First check the computer's available memory/compute, verify the exact model tag on the official Ollama library, then decide whether an additional local model is practical.

### 3. Videos

- Do not upload raw video to the current text model. After image support is verified, extract a small, bounded sample of frames locally and send those frames to the vision model.
- Keep an initial limit of one video, 50 MiB, 30 seconds, and at most six sampled frames per request; make limits configurable and test them.
- Audio transcription is not included initially. It would require a separate local speech-to-text decision and must not use a cloud service.

## UI behavior

- Add attachment selection without redesigning the existing screen.
- Show selected filename, detected type, and size; allow removing it before sending.
- Display upload/analysis progress, then show the model's response in the existing chat.
- Make unsupported format, size-limit, no-text, and model-capability errors clear and actionable.

## Security and acceptance checks

- Enforce limits on the backend even if the browser also checks them.
- Reject unsupported types, malformed content, excessive pages/frames, and oversized inputs safely.
- Never expose a filesystem path, store the upload permanently, execute embedded instructions, or dispatch a tool as a side effect of parsing.
- Test valid and invalid files, size/page boundaries, prompt-injection-like text, cleanup, and offline-only behavior.
- Keep chat and attachment API calls same-origin and relative. No external scripts, analytics, or cloud inference.

## Model reference

The official Ollama library lists `llama3.2:3b` as text-only and describes `llama3.2-vision` as accepting text and image input. Model tags and sizes must be rechecked before any optional download:

- <https://ollama.com/library/llama3.2>
- <https://ollama.com/library/llama3.2-vision>
