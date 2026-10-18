"""Terminal chat client for LEGO AI Agent."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence

from lego import APP_NAME, __version__
from lego.agent.llm import OllamaError, chat
from lego.agent.prompts import CHAT_SYSTEM_PROMPT

_MAX_HISTORY_MESSAGES = 20
_EXIT_COMMANDS = {"/exit", "/quit", "exit", "quit"}


def _new_history() -> list[dict[str, str]]:
    return [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]


def _trim_history(history: list[dict[str, str]]) -> None:
    """Keep the system prompt and a limited number of recent chat messages."""
    while len(history) > _MAX_HISTORY_MESSAGES + 1:
        del history[1:3]


def _send(history: list[dict[str, str]]) -> str:
    return asyncio.run(chat(history))


def _run_one_message(message: str) -> int:
    history = _new_history()
    history.append({"role": "user", "content": message})
    try:
        print(_send(history))
    except OllamaError as exc:
        print(f"{APP_NAME}: {exc}", file=sys.stderr)
        return 1
    return 0


def _run_interactive() -> int:
    history = _new_history()
    print(f"{APP_NAME} {__version__} — local chat")
    print("Type /exit or /quit to end the chat.")

    while True:
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not message:
            continue
        if message.casefold() in _EXIT_COMMANDS:
            return 0

        history.append({"role": "user", "content": message})
        _trim_history(history)
        try:
            reply = _send(history)
        except OllamaError as exc:
            history.pop()
            print(f"{APP_NAME}: {exc}", file=sys.stderr)
            continue

        history.append({"role": "assistant", "content": reply})
        print(f"{APP_NAME}: {reply}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"Chat with {APP_NAME} locally.")
    parser.add_argument(
        "--message",
        help="Send one message and exit instead of starting interactive chat.",
    )
    args = parser.parse_args(argv)

    if args.message is not None:
        message = args.message.strip()
        if not message:
            parser.error("--message cannot be empty.")
        return _run_one_message(message)

    return _run_interactive()


if __name__ == "__main__":
    raise SystemExit(main())
