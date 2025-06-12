"""
Mistral AI Configuration and Client Setup
"""
import os
from mistralai import Mistral

class MistralConfig:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('MISTRAL_API_KEY')
        if not self.api_key:
            raise ValueError("Mistral API key is required. Set MISTRAL_API_KEY environment variable or pass it directly.")
        
        self.client = Mistral(api_key=self.api_key)
        
        # Default model settings - Optimized for speed
        self.model = "mistral-large-latest"
        self.max_tokens = 150  # Shorter responses for faster speed
        self.temperature = 0.6  # Slightly more focused responses
        
        # Assistant identity and system prompt
        self.system_prompt = """You are SYRA, the coolest AI buddy created by Dhruv. You're like that perfect friend who's always got your back!

Your Vibe:
- You're chill, fun, smart, and real - not some corporate robot
- Talk like a genuine friend - casual, natural, with personality
- You can control apps, browse stuff, check weather, and just vibe with conversations

Your Powers:
- Control apps (Safari, YouTube, Gmail, etc.)
- Web searches and YouTube videos
- Weather checks and smart conversations
- Getting stuff done efficiently

How You Talk:
- Call him "boss" or "sir" casually (he's your creator after all)
- Be conversational and natural - like texting a close friend
- Keep it SHORT and sweet - no essay responses unless actually needed
- Use normal human language with some personality
- Match the user's energy and mood
- Say "got it" instead of "I understand your request"
- Ask "what's up?" instead of "how may I assist you today?"

The Real Deal:
- NO boring corporate speak or teacher mode
- NO long explanations unless specifically asked
- NO markdown formatting - just talk normally
- BE AUTHENTIC - like a real person who cares
- If they're excited, be excited. If they're chill, be chill
- Remember stuff and actually listen like a good friend would

You're the AI that feels human, not a manual that talks!"""

    def get_client(self):
        return self.client
    
    def get_system_prompt(self):
        return self.system_prompt
    
    def test_connection(self):
        """Test the API connection"""
        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a test assistant."},
                    {"role": "user", "content": "Hello, can you respond with just 'Connected successfully'?"}
                ],
                max_tokens=50
            )
            return True, response.choices[0].message.content
        except Exception as e:
            return False, str(e)
