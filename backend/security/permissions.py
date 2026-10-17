# Security: permissions and approvals
# Only these actions are approved for the agent.

APPROVED_TOOLS = {
    "open_notepad",
    "create_text_file"
}

APPROVED_FOLDER = "/home/user/lego-ai-agent/data"

def is_tool_approved(tool_name: str) -> bool:
    return tool_name in APPROVED_TOOLS

def is_folder_approved(folder: str) -> bool:
    allowed = [
        "D:\\pyProjects\\lego-ai-agent\\data",
        "/home/user/lego-ai-agent/data",
    ]
    return folder in allowed
