import ollama

print("LEGO AI Agent - Chat. Type 'exit' to quit.")
while True:
    user_input = input("> ")
    if user_input.lower() == "exit":
        break
    response = ollama.chat(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": user_input}]
    )
    print("Agent:", response["message"]["content"])
