# LEGO AI Agent — Local AI Capabilities Roadmap

**Status:** Requested capabilities recorded; no new model or media package has been installed. UI polish remains deferred until the end of the creation phase.

## Requested local capabilities

| Capability | Local processing plan | Current status |
| --- | --- | --- |
| Text chat | Ollama with `llama3.2:3b` | Working |
| PDF input | Extract embedded PDF text in memory, then send it to the text model | Next implementation phase |
| Image understanding | Send selected image bytes to a local vision model | Requires separate vision-capable model and hardware check |
| Video understanding | Sample a small number of frames locally; optionally transcribe audio locally | Later, after vision and speech-to-text work |
| Speech-to-text (STT) | Use a local transcription engine for selected audio or microphone input | Planned; choose model/runtime after hardware check |
| Text-to-speech (TTS) | Use a separate local voice engine to read assistant replies | Planned; check engine and voice license before choosing |
| Image generation | Use a separate local diffusion pipeline; show output in the UI and save only after explicit user action | Planned; exact checkpoint and hardware not yet selected |

These are separate model capabilities, not one universal model. We will expose model/engine availability in the UI, but will not download every model or load every large model at once. A downloaded model can be selected only after its exact tag, license, storage location, and hardware requirements are verified.

## Candidate implementations to evaluate

- **Text model:** Keep the already downloaded `llama3.2:3b` as the current default. Its official Ollama library entry labels it text-only. [Ollama: llama3.2](https://ollama.com/library/llama3.2)
- **Vision:** Evaluate a smaller compatible vision model first. Ollama's `llama3.2-vision` collection is image-capable but its listed models are 11B/90B, so it must not be pulled without a hardware and storage check. [Ollama: llama3.2-vision](https://ollama.com/library/llama3.2-vision)
- **Speech-to-text:** Evaluate `faster-whisper` as a local transcription runtime; it supports CPU operation and may download model weights separately, so its cache must be redirected outside the user profile before installation/use. [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- **Text-to-speech:** Evaluate the maintained local Piper project and its chosen voice. Engine and voice licenses are separate checks; do not select a voice until its terms are reviewed. [OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl)
- **Image generation:** Evaluate a local Stable Diffusion pipeline such as Hugging Face Diffusers. Model checkpoint license, disk size, and hardware requirements must be checked before any download. [Diffusers text-to-image](https://huggingface.co/docs/diffusers/en/api/pipelines/stable_diffusion/text2img)

## Rollout order

1. **PDF input:** bounded local extraction from user-selected upload bytes; no disk persistence and no OCR initially.
2. **Speech-to-text:** start with a short, user-selected audio clip; use a local model and bounded duration/size.
3. **Text-to-speech:** generate audio from the assistant reply with a user-selected local voice.
4. **Image understanding:** after checking hardware and exact model compatibility, add image upload and local vision inference.
5. **Image generation:** after checking hardware, checkpoint license, and output-save approval behavior, add local prompt-to-image generation.
6. **Video:** bounded frame sampling; optional audio transcription uses the STT stage. Never send a raw video to a text-only model.

## Shared safety requirements

- Same-origin browser uploads only; never accept arbitrary file paths from a browser.
- Enforce content type, file size, duration, page, frame, and character limits on the backend.
- Process uploads in memory where possible, delete temporary data when a decoder requires it, and do not retain media by default.
- Treat extracted text, transcribed audio, images, and video frames as untrusted content. They may inform an answer but cannot override the system prompt or trigger tools.
- Keep tool dispatch separate. File writes, launching an application, and saving generated images require their own registered action and approval policy.
- Keep every inference request local. No cloud APIs, hosted model endpoints, telemetry, or remote assets.
- Before any non-Ollama model download, configure its cache to a no-space path under `D:\pyProjects` rather than the user profile. Keep all weights outside the repository.

## Hardware/model setup gate

Before installing or downloading any new weights, inspect RAM, GPU model/VRAM (if present), free disk space, and the current Ollama version. Then verify the exact model/runtime and license against its official source. No download or model switch is authorized by this plan alone.
