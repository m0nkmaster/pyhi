from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT

class ClaudeWrapper:
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def get_completion(self, messages: list) -> str:
        """Get a completion from the Claude API using the Messages API."""
        # Extract system message and user messages
        system_message = next((msg['content'] for msg in messages if msg['role'] == 'system'), None)
        user_messages = [
            {"role": "user", "content": msg['content']}
            for msg in messages if msg['role'] == 'user'
        ]
        
        response = self.client.messages.create(
            model=self.model,
            system=system_message,
            messages=user_messages,
            max_tokens=150
        )
        return response.content[0].text
