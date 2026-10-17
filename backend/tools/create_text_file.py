import os

APPROVED_FOLDER = "/home/user/lego-ai-agent/data"

def create_text_file(filename, content, approved_folder):
    """
    Safe tool: create a text file ONLY in the approved folder.
    Requires user confirmation before writing.
    """
    allowed_folders = [
        "D:\\pyProjects\\lego-ai-agent\\data",
        "/home/user/lego-ai-agent/data",
    ]
    
    # Validate folder
    if approved_folder not in allowed_folders:
        return f"Rejected: folder '{approved_folder}' is not approved. Only allowed: {allowed_folders}"
    
    # Confirm content before creating
    preview = content[:50] + "..." if len(content) > 50 else content
    return f"Confirmation required: create file '{filename}' with content '{preview}' in '{approved_folder}'? Confirm with 'yes' to proceed."

def confirm_and_create(filename, content):
    """Only called after user confirms."""
    filepath = os.path.join(APPROVED_FOLDER, filename)
    # Security check: no path traversal
    if ".." in filepath or "/" in filename and not os.path.dirname(filepath).startswith(APPROVED_FOLDER):
        return "Rejected: invalid file path."
    
    os.makedirs(APPROVED_FOLDER, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return f"File created: {filepath}"
