from anthropic import Anthropic

client = Anthropic()

conversation_history = []
MAX_HISTORY = 20

SYSTEM_PROMPT = """
You are a helpful assistant.
"""

while True:
    user_input = input("You: ").strip()

    if user_input.lower() in {"quit", "exit"}:
        break

    conversation_history.append({
        "role": "user",
        "content": user_input
    })

    try:
        response = client.messages.create(
            model="claude-opus-5",
            system=SYSTEM_PROMPT,
            max_tokens=2048,
            messages=conversation_history,
        )

        assistant_message = response.content[0].text

        conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        print(f"\nClaude: {assistant_message}\n")

        # Keep only the most recent messages
        if len(conversation_history) > MAX_HISTORY:
            conversation_history = conversation_history[-MAX_HISTORY:]

    except Exception as e:
        print(f"\nError: {e}\n")
