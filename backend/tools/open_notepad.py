import subprocess

def open_notepad():
    """Safe tool: open Notepad. Only this action is allowed."""
    try:
        subprocess.run(["notepad.exe"], check=False)
        return "Notepad opened."
    except Exception as e:
        return f"Error opening Notepad: {e}"
