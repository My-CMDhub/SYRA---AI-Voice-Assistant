"""
AI Handler for Edith Assistant using Mistral AI
"""
import json
from mistral_config import MistralConfig
from translation_handler import TranslationHandler

class EdithAIHandler:
    def __init__(self, api_key):
        self.mistral_config = MistralConfig(api_key=api_key)
        self.client = self.mistral_config.get_client()
        self.translator = TranslationHandler()
        
        # Conversation history for context awareness
        self.conversation_history = []
        
        # REMOVED - Now using the enhanced detect_system_command method instead
        # This old dictionary was too broad and caused classification issues
        self.system_commands = {}
    
    def detect_system_command(self, query):
        """Enhanced system command detection with priority for weather queries"""
        query_lower = query.lower().strip()
        
        # PRIORITY 1: Weather queries - these should NEVER go to web search
        weather_keywords = [
            'weather', 'temperature', 'temp', 'hot', 'cold', 'sunny', 'rainy', 'cloudy',
            'forecast', 'degrees', 'celsius', 'fahrenheit', 'humid', 'humidity',
            'precipitation', 'rain', 'snow', 'storm', 'wind', 'windy'
        ]
        
        # Check for weather keywords first, but exclude certain contexts
        for keyword in weather_keywords:
            if keyword in query_lower:
                # Special check for "climate" - only weather-related if asking about current conditions
                if keyword == 'climate':
                    # Skip if it's about "climate change" or general climate topics
                    if any(phrase in query_lower for phrase in ['climate change', 'climate crisis', 'climate action', 'about climate']):
                        continue
                
                print(f"🌤️ AI Handler: Weather keyword '{keyword}' detected - routing to weather API")
                return 'weather_query'
        
        # Check for weather-specific patterns
        weather_patterns = [
            r'\bhow\'?s\s+(?:the\s+)?weather',
            r'\bwhat\'?s\s+(?:the\s+)?weather',
            r'\bcheck\s+(?:the\s+)?weather',
            r'\bget\s+(?:the\s+)?weather',
            r'\bfind\s+(?:the\s+)?weather',
            r'\bweather\s+(?:in|of|for|at)',
            r'\btemperature\s+(?:in|of|for|at)',
            r'\bhow\s+(?:hot|cold|warm)\s+is\s+it',
            r'\bis\s+it\s+(?:hot|cold|warm|sunny|rainy)',
            r'\bwill\s+it\s+rain',
            r'\bis\s+it\s+raining'
        ]
        
        import re
        for pattern in weather_patterns:
            if re.search(pattern, query_lower):
                print(f"🌤️ AI Handler: Weather pattern '{pattern}' detected - routing to weather API")
                return 'weather_query'
        
        # PRIORITY 2: INFORMATION QUERIES - Should go to search/AI, NOT open apps (but NOT weather)
        information_patterns = [
            r'\bwho\s+(?:is|are|was|were|owns?|created?)\s+',
            r'\bwhat\s+(?:is|are|was|were)\s+',
            r'\bhow\s+(?:is|are|was|were|do|does|did)\s+',
            r'\bwhen\s+(?:is|was|did|does|do)\s+',
            r'\bwhere\s+(?:is|are|was|were)\s+',
            r'\bwhy\s+(?:is|are|was|were|do|does|did)\s+',
            r'\btell\s+me\s+about\s+',
            r'\bget\s+(?:me\s+)?(?:information|info)\s+(?:about\s+)?',
            r'\bi\s+want\s+to\s+(?:know|learn|understand)\s+',
            r'\bcan\s+you\s+(?:tell|explain|describe)\s+',
            r'\binformation\s+about\s+',
            r'\bexplain\s+(?:about\s+)?',
            r'\bdescribe\s+',
        ]
        
        # Check if it's an information query (excluding weather queries already handled)
        for pattern in information_patterns:
            if re.search(pattern, query_lower):
                return 'search_safari'  # Route to search/AI for information
        
        # EXPLICIT APP COMMANDS - Clear intent to open/close apps (ONLY if NOT video/search related)
        explicit_app_patterns = {
            'open_app': [
                r'\b(?:open|start|launch|run)\s+(?:the\s+)?(?:application\s+|app\s+)?(\w+(?:\s+\w+){0,2})\s*(?:application|app)?\s*$',
                r'\blet\'s\s+(?:open|start|launch)\s+(?:the\s+)?(\w+(?:\s+\w+){0,2})\s*$',
                r'\bcan\s+you\s+(?:open|start|launch)\s+(?:the\s+)?(\w+(?:\s+\w+){0,2})\s*$',
            ],
            'close_app': [
                r'\b(?:close|quit|exit|shut\s+down|turn\s+off)\s+(?:the\s+)?(\w+(?:\s+\w+){0,2})',
                r'\blet\'s\s+(?:close|quit|exit)\s+(?:the\s+)?(\w+(?:\s+\w+){0,2})',
            ],
        }
        
        # Check explicit app commands ONLY if it's NOT a video/search query
        video_keywords = ['video', 'videos', 'watch', 'latest', 'news', 'of', 'about']
        has_video_context = any(keyword in query_lower for keyword in video_keywords)
        
        if not has_video_context:  # Only check app commands if no video context
            for command_type, patterns in explicit_app_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, query_lower):
                        return command_type
        
        # SEARCH PATTERNS - All other search/lookup/video requests
        search_patterns = [
            r'\b(?:search|find|look\s+(?:up|for)|google|browse)\s+(?:for\s+|about\s+)?',
            r'\bi\s+want\s+(?:you\s+)?to\s+(?:search|find|look\s+up)\s+',
            r'\blet\'s\s+search\s+(?:for\s+|about\s+|out\s+)?',
            r'\bcan\s+you\s+(?:search|find|look\s+up)\s+',
            r'\bi\s+want\s+to\s+(?:watch|see)\s+(?:a\s+)?video\s+',
            r'\bshow\s+me\s+',
            r'\bstart\s+a\s+video\s+',
            r'\bwatch\s+(?:a\s+)?video\s+',
            r'\bvideo\s+of\s+',
            r'\bvideos\s+of\s+',
            r'\blet\'s\s+start\s+(?:a\s+)?video\s+',
            r'\bhey\s+let\'s\s+start\s+(?:a\s+)?video\s+',
            r'\bcurrent\s+',
            r'\blatest\s+',
            r'\btoday\'s\s+',
            r'\bwho\s+is\s+the\s+owner\s+of\s+',
            r'\bwho\s+owns\s+',
            r'\bfind\s+out\s+(?:about\s+)?',
            r'\bcan\s+you\s+find\s+out\s+',
        ]
        
        # Check search patterns
        for pattern in search_patterns:
            if re.search(pattern, query_lower):
                return 'search_safari'
        
        # SPECIFIC APP COMMANDS - Only very specific mentions
        specific_commands = {
            'open_safari': ['open safari', 'start safari', 'launch safari'],
            'close_safari': ['close safari', 'quit safari', 'exit safari'],
            'open_youtube': ['open youtube', 'start youtube', 'launch youtube'],
            'close_youtube': ['close youtube', 'quit youtube', 'exit youtube'],
            'open_gmail': ['open gmail', 'start gmail', 'launch gmail'],
            'weather_query': ['weather in', 'what\'s the weather', 'how is the weather', 'check weather'],
            'goodbye': ['goodbye', 'good bye', 'see you later', 'thank you goodbye']
        }
        
        # Check specific commands
        for command_type, keywords in specific_commands.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return command_type
        
        return None
    
    def get_ai_response(self, user_input, language='en'):
        """Get AI response from Mistral while maintaining context"""
        
        # Translate to English if needed
        if language == 'hi':
            english_input = self.translator.translate_text(user_input, src='hi', dest='en')
        else:
            english_input = user_input
        
        # Check for system commands first
        system_command = self.detect_system_command(english_input)
        
        # Build conversation context
        messages = [
            {"role": "system", "content": self.mistral_config.get_system_prompt()}
        ]
        
        # Add conversation history (last 6 messages for context)
        for msg in self.conversation_history[-6:]:
            messages.append(msg)
        
        # Add current user message
        current_message = {"role": "user", "content": english_input}
        messages.append(current_message)
        
        try:
            # Get AI response
            response = self.client.chat.complete(
                model=self.mistral_config.model,
                messages=messages,
                max_tokens=self.mistral_config.max_tokens,
                temperature=self.mistral_config.temperature
            )
            
            ai_response = response.choices[0].message.content
            
            # Add to conversation history
            self.conversation_history.append(current_message)
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            # Return both AI response and system command info
            return {
                'ai_response': ai_response,
                'system_command': system_command,
                'original_query': user_input,
                'english_query': english_input
            }
            
        except Exception as e:
            # Fallback response if AI fails
            fallback_response = "I apologize sir, I'm having trouble processing that right now. Could you please try again?"
            return {
                'ai_response': fallback_response,
                'system_command': system_command,
                'original_query': user_input,
                'english_query': english_input
            }
    
    def clear_conversation_history(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def get_conversation_summary(self):
        """Get a summary of recent conversation"""
        if len(self.conversation_history) < 2:
            return "No recent conversation."
        
        recent_messages = self.conversation_history[-4:]  # Last 2 exchanges
        summary = "Recent conversation:\n"
        for msg in recent_messages:
            role = "You" if msg["role"] == "user" else "Edith"
            summary += f"{role}: {msg['content'][:100]}...\n"
        
        return summary

# Test the AI handler
if __name__ == "__main__":
    # Test with the API key from environment variable
    import os
    api_key = os.getenv('MISTRAL_API_KEY')
    if not api_key:
        print("❌ MISTRAL_API_KEY environment variable not set")
        print("Please set it with: export MISTRAL_API_KEY='your_api_key_here'")
        exit(1)
    
    ai_handler = EdithAIHandler(api_key)
    
    # Test different types of queries
    test_queries = [
        "Hello, how are you?",
        "What's your name?",
        "Open Safari please",
        "What can you do for me?",
        "Tell me about the weather",
    ]
    
    print("🤖 Testing AI Handler:")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\n👤 User: {query}")
        result = ai_handler.get_ai_response(query)
        print(f"🤖 Edith: {result['ai_response']}")
        if result['system_command']:
            print(f"⚙️  System Command Detected: {result['system_command']}")
        print("-" * 30)
