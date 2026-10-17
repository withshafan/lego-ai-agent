from fastapi import FastAPI
from pydantic import BaseModel
import ollama
from backend.tools.open_notepad import open_notepad
from backend.tools.create_text_file import confirm_and_create

app = FastAPI()

# Security: stays on localhost. Never expose to internet.

class ChatRequest(BaseModel):
    message: str

class ToolRequest(BaseModel):
    tool_name: str
    params: dict

@app.post("/chat")
async def chat(req: ChatRequest):
    response = ollama.chat(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": req.message}]
    )
    return {"reply": response["message"]["content"]}

@app.post("/propose_tool")
async def propose_tool(req: ToolRequest):
    """Propose an action. Do NOT run it yet."""
    if req.tool_name == "open_notepad":
        return {"proposal": "Open Notepad? Confirm with yes.", "action": "open_notepad"}
    elif req.tool_name == "create_text_file":
        filename = req.params.get("filename", "")
        content = req.params.get("content", "")
        folder = req.params.get("folder", "/home/user/lego-ai-agent/data")
        preview = content[:50] + "..." if len(content) > 50 else content
        return {
            "proposal": f"Create '{filename}' with content '{preview}' in '{folder}'? Confirm with yes.",
            "action": "create_text_file",
            "params": req.params
        }
    else:
        return {"error": "Unknown or unapproved tool."}

@app.post("/confirm_tool")
async def confirm_tool(req: ToolRequest):
    """Only runs after user confirms with 'yes'."""
    if req.params.get("confirmed") != "yes":
        return {"status": "rejected", "message": "Confirmation 'yes' required."}
    
    if req.tool_name == "open_notepad":
        result = open_notepad()
        return {"status": "done", "result": result}
    elif req.tool_name == "create_text_file":
        filename = req.params.get("filename", "")
        content = req.params.get("content", "")
        result = confirm_and_create(filename, content)
        return {"status": "done", "result": result}
    else:
        return {"error": "Unknown tool."}
