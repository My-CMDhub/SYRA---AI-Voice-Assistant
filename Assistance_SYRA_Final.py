from gtts import gTTS
import os
import speech_recognition as sr
from langdetect import detect
import webbrowser
import subprocess
import random
import sys
import requests
import json
import re
from datetime import datetime
import time
import urllib.parse

# Import our AI components
from ai_handler import EdithAIHandler
from translation_handler import TranslationHandler

# Get Mistral API key from environment variable
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
if not MISTRAL_API_KEY:
    print("❌ MISTRAL_API_KEY environment variable not set")
    print("Please set it with: export MISTRAL_API_KEY='your_api_key_here'")
    print("Or add it to your .env file")
    sys.exit(1)

CONVERSATION_LOG_FILE = "conversations.txt"

MAX_TIMEOUT_ATTEMPTS = 3
conversation_context = []
timeout_manager = None

def clean_markdown_response(text):
    """Remove markdown formatting from AI responses"""
    # Remove markdown headers (###, ##, #)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    # Remove bold/italic markers (**, *, __)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
    text = re.sub(r'__([^_]+)__', r'\1', text)      # __bold__
    text = re.sub(r'_([^_]+)_', r'\1', text)        # _italic_
    
    # Remove bullet points and list markers
    text = re.sub(r'^[\s]*[-*+]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s*', '', text, flags=re.MULTILINE)
    
    # Remove extra whitespace and line breaks
    text = re.sub(r'\n\s*\n', '. ', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def detect_user_disengagement(query):

    if not query:
        return False
    
    prompt = f"""

    Analyze if the user wants to STOP or DISENGAGE from the conversation with the AI assistant.
    
    User said: "{query}"
    
    Reply ONLY with "YES" if they want to stop/disengage, or "NO" if they want to continue.
    
    DISENGAGEMENT SIGNALS (YES):
    - "I don't want to say anything"
    - "I'm not in good mood to talk"
    - "Leave me alone"
    - "Stop talking"
    - "I don't want to chat"
    - "Not interested"
    - "Go away"
    - "I'm busy"
    - "Not now"
    - "Goodbye" (when said alone)
    - "Bye" (when said alone)
    - "That's all for now"
    - "I'm done"
    
    CONTINUE SIGNALS (NO):
    - "Close [app name]" → NO (app command, not disengagement)
    - "Let's close [app name]" → NO (app command, not disengagement)
    - "Open [app name]" → NO (app command)
    - "Search for something" → NO (search request)
    - Normal questions or conversations → NO
    - Requests for help → NO
    - Any productive interaction → NO
    
    CRITICAL: If the user mentions closing/opening specific applications (like "close Gemini", "close Gmail", "open Safari"), this is NOT disengagement - they want to control apps.
    
    """
    
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 10,
                "temperature": 0.1
            },
            timeout=8
        )

        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content'].strip().upper()
            return "YES" in ai_response
        else:
            return False
        
    except Exception as e:
        print(f"AI disengagement detection timeout - using fallback")
        return False
    
def generate_contextual_confirmation(conversation_history):

    if not conversation_history:
        return "Are you still there, sir? I can help you with anything you need."
    
    recent_context = conversation_history[-3:] if len(conversation_history) > 3 else conversation_history
    context_text = " | ".join([f"You: {item['user']} -> SYRA: {item['syra'][:50]}..." for item in recent_context])

    prompt = f"""
    Based on our recent conversation, generate a natural check-in message.
    
    Recent conversation context: {context_text}
    
    Create a brief, caring message that:
    1. Acknowledges we were discussing something specific
    2. Asks if they want to continue or need help with something else
    3. Sounds natural and personal
    
    Examples:
    - "Are you still there? Were you interested in learning more about those habits we discussed?"
    - "I was helping you with app management - did you want to continue or try something else?"
    - "We were talking about search features - are you still there sir?"
    
    Generate one natural check-in message:"""
    
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 50,
                "temperature": 0.7
            },
            timeout=8
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        else:
            return "Are you still there sir? Is there anything I can help you with?"
            
    except Exception as e:
        print(f"Context generation timeout - using fallback")
        return "Are you still there sir? Is there anything I can help you with?"
    
class TimeoutManager:

    def __init__(self):
        self.failed_attempts = 0
        self.max_attempts = MAX_TIMEOUT_ATTEMPTS
        self.reset()

    def reset(self):
        self.failed_attempts = 0

    def increment_failure(self):
        self.failed_attempts+=1
        print(f"🔴 Timeout attempt {self.failed_attempts}/{self.max_attempts}")

    def should_exit(self):

        return self.failed_attempts >= self.max_attempts
    
    def get_timeout_response(self, conversation_history):

        if self.failed_attempts == 1:
            return "I couldn't hear you properly sir. Please try again."
        
        elif self.failed_attempts == 2:
            return generate_contextual_confirmation(conversation_history)
        
        elif self.failed_attempts >= 3:
            farewell_messages = [
               "I understand you might be busy or not in the mood to chat right now. Feel free to wake me up anytime you need assistance. Have a wonderful day boss!",
                "It seems like you might have stepped away or are busy with something important. I'll be here whenever you need help. Take care boss!",
                "I respect that you might not want to continue right now. Remember, I'm always here to help with web searches, opening applications, or just having a chat. Have a great day sir!"
            ]

            return random.choice(farewell_messages)
        return "I couldn't hear you properly sir. Please try again by refining your query."
    
def update_conversation_context(user_input, assistant_response):

    global conversation_context

    conversation_context.append({
        'user': user_input,
        'syra': assistant_response,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    # Keep only last 5 exchanges to avoid memory issues
    if len(conversation_context) > 5:
       
        conversation_context = conversation_context[-5:]

    print(f"📝 Context updated: {len(conversation_context)} exchanges tracked")

def log_conversation(user_input, assistant_response, response_time=None, query_type=None, ai_refined=None):
    """Enhanced conversation logging with performance metrics"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(CONVERSATION_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n[{timestamp}]\n")
            f.write(f"YOU: {user_input}\n")
            f.write(f"SYRA: {assistant_response}\n")
            
            # Add performance metrics
            if response_time:
                f.write(f"⏱️ Response Time: {response_time:.2f} seconds\n")
            
            if query_type:
                f.write(f"🎯 Query Type: {query_type}\n")
                
            if ai_refined:
                f.write(f"🧠 AI Refined: {ai_refined}\n")
            
            f.write("-" * 50 + "\n")
            
    except Exception as e:
        print(f"Error logging conversation: {e}")

def check_microphone_permission():
    """Check if microphone permission is granted and guide user if not"""
    try:
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("Testing microphone access...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("✅ Microphone access granted!")
            return True
    except Exception as e:
        print("❌ Microphone access denied or not available!")
        print(f"Error: {e}")
        print("\n📋 To fix this issue:")
        print("1. Open System Preferences/Settings")
        print("2. Go to Security & Privacy > Privacy")
        print("3. Click on 'Microphone' in the left sidebar")
        print("4. Find 'Visual Studio Code' or 'Code' in the list")
        print("5. Check the box next to it to enable microphone access")
        return False

def speak(text):
    """SYRA speak in english with faster speed"""
    try:
        clean_text = clean_markdown_response(text)
        # Use faster speech settings with speed optimization
        tts = gTTS(text=clean_text, lang='en', slow=False)
        tts.save('output.mp3')
        # Use faster audio playback - mpg123 doesn't support --rate, use afplay with speed
        try:
            # Try afplay first (macOS built-in, supports speed control)
            os.system('afplay -r 1.2 output.mp3')
        except:
            # Fallback to mpg123 without speed control
            os.system('mpg123 --quiet output.mp3')
    except Exception as e:
        print(f"TTS Error: {e}")
        print(f"SYRA: {text}")

def recognition():
    """Optimized voice recognition function"""
    recognizer = sr.Recognizer()
    
    # Optimize recognizer settings for better performance
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.6  # Faster response
    
    with sr.Microphone() as source:
        print("Listening...")
        # Faster ambient noise adjustment
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = recognizer.listen(source, phrase_time_limit=6, timeout=10)  # Increased timeout
            print("Recognizing...")
            query = recognizer.recognize_google(audio, language='en-IN')
            detect_language = detect(query)
            print(f"Creator: {query}")
            return query.lower(), detect_language
        except sr.WaitTimeoutError:
            print("Listening timeout - please try again")
            return None, None
        except sr.UnknownValueError:
            print("Could not understand audio")
            return None, None
        except sr.RequestError:
            print("Could not connect to the server")
            return None, None

def is_video_search_query(query):
    """Enhanced video search detection with priority for video keywords"""
    
    # First, check for explicit video/YouTube keywords with HIGHEST PRIORITY
    video_keywords = [
        'video', 'videos', 'video of', 'a video of', 'watch', 'movie', 'film', 'scene',
        'youtube', 'on youtube', 'on YouTube', 'from youtube', 'youtube video',
        'let\'s find out video', 'find out video', 'check out video', 'search video'
    ]
    
    query_lower = query.lower()
    
    # PRIORITY 1: Direct video keyword detection (fastest, most reliable)
    for keyword in video_keywords:
        if keyword in query_lower:
            print(f"🎬 DIRECT video keyword detected: '{keyword}' in query")
            return True
    
    # PRIORITY 2: YouTube-specific patterns (even with "search")
    youtube_patterns = [
        r'\bon\s+youtube\b',
        r'\bfrom\s+youtube\b',
        r'\byoutube\s+video\b',
        r'\bsearch\s+.*\s+on\s+youtube\b',
        r'\bfind\s+.*\s+on\s+youtube\b',
        r'\blook\s+.*\s+on\s+youtube\b'
    ]
    
    import re
    for pattern in youtube_patterns:
        if re.search(pattern, query_lower):
            print(f"🎬 YOUTUBE pattern detected: '{pattern}' in query")
            return True
    
    # PRIORITY 3: Video action phrases
    video_action_patterns = [
        r'\blet\'s\s+find\s+out\s+video\b',
        r'\bcheck\s+out\s+video\b',
        r'\bfind\s+.*\s+video\b',
        r'\bsearch\s+.*\s+video\b',
        r'\bwatch\s+.*\s+video\b'
    ]
    
    for pattern in video_action_patterns:
        if re.search(pattern, query_lower):
            print(f"🎬 VIDEO action pattern detected: '{pattern}' in query")
            return True
    
    # PRIORITY 4: AI fallback for complex cases
    prompt = f"""
    IMPORTANT: Analyze if user wants VIDEO content or TEXT/INFO content.

    Query: "{query}"
    
    Reply ONLY with "YES" for video content or "NO" for text/info content.
    
    VIDEO CONTENT (YES):
    - Contains: "video", "videos", "watch", "movie", "film", "scene", "youtube", "on youtube"
    - Contains: "find out video", "check out video", "search video", "video of"
    - Examples: "I want to watch a video of iPhone 15 Pro review" → YES
    - Examples: "video of MacBook Pro review" → YES
    - Examples: "let's find out video of cats" → YES
    - Examples: "check out video of Tesla" → YES
    - Examples: "search apple's news on Youtube" → YES
    - Examples: "find out openai latest update on youtube" → YES
    - Examples: "search video of funny dogs" → YES
    
    TEXT/INFO CONTENT (NO):
    - Wants: specs, price, information, facts, reviews (without video keywords)
    - Examples: "Tesla stock price" → NO
    - Examples: "iPhone 15 specifications" → NO
    - Examples: "search Tesla news" → NO (no video keyword)
    
    CRITICAL RULE: If query contains ANY video-related keywords (video, youtube, watch, movie, film) = YES, even if it also contains "search" or "find".
    """
    
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 10,
                "temperature": 0.1
            },
            timeout=8
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content'].strip().upper()
            return "YES" in ai_response
        else:
            return False
            
    except Exception as e:
        print(f"AI video detection timeout - using fallback")
        return False

def is_weather_query(query):
    """Detect weather-related queries with high priority - these should NEVER go to web search"""
    weather_keywords = [
        'weather', 'temperature', 'temp', 'hot', 'cold', 'sunny', 'rainy', 'cloudy',
        'forecast', 'climate', 'degrees', 'celsius', 'fahrenheit', 'humid', 'humidity',
        'precipitation', 'rain', 'snow', 'storm', 'wind', 'windy'
    ]
    
    query_lower = query.lower()
    
    # Check for weather keywords
    for keyword in weather_keywords:
        if keyword in query_lower:
            print(f"🌤️ WEATHER keyword detected: '{keyword}' in query")
            return True
    
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
            print(f"🌤️ WEATHER pattern detected: '{pattern}' in query")
            return True
    
    return False

def is_search_related_query(query):
    """Determine if query is search-related using AI for 100% accuracy - EXCLUDES weather queries"""
    
    # PRIORITY 1: Check if it's a weather query first - these should NEVER go to web search
    if is_weather_query(query):
        print(f"🌤️ Weather query detected - routing to weather API, NOT web search")
        return False  # Weather queries are handled separately, not web search
    
    prompt = f"""
    Analyze this user query and determine if it requires a web search, video search, or real-time information.
    
    Query: "{query}"
    
    Respond with only "YES" if it needs any kind of search/information lookup, or "NO" if it doesn't.
    
    IMPORTANT: Weather queries should be marked as "NO" since they use dedicated weather API.
    
    SEARCH/INFO QUERIES (YES):
    - "I want you to find Tesla stock price" → YES
    - "Let's search about climate change" → YES  
    - "I want to watch Avengers movie" → YES
    - "I want to watch a video of dogs" → YES
    - "hey I want to watch a video of iPhone 15 Pro review" → YES
    - "let's search out today's market" → YES
    - "I want to check price of IBM" → YES
    - "what's today's Australian news" → YES
    - "who won the latest football match" → YES
    - "get me latest Tesla stock price" → YES
    - "what's happening in the world" → YES
    - "current Bitcoin price" → YES
    - "latest iPhone features" → YES
    - "search for something" → YES
    - "find information about" → YES
    - "look up" → YES
    
    NON-SEARCH QUERIES (NO):
    - "Open calculator" → NO
    - "Close Safari" → NO
    - "How are you" → NO
    - "Open Microsoft Word" → NO
    - "Launch an app" → NO
    - "Good morning" → NO
    - "Thank you" → NO
    - "what's the weather like" → NO (uses weather API)
    - "temperature in Melbourne" → NO (uses weather API)
    - "how's the weather" → NO (uses weather API)
    
    DECISION RULE: If user wants to FIND, SEARCH, WATCH, get current/real-time information, prices, news, or any content from the internet = YES. If they want to open/close apps, have simple conversations, or ask about WEATHER = NO.
    """
    
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 10,
                "temperature": 0.1
            },
            timeout=8
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content'].strip().upper()
            return "YES" in ai_response
        else:
            return False
            
    except Exception as e:
        print(f"AI search detection timeout - using fallback")
        return False

def get_ai_refined_search_query(query):
    """Get AI-refined search query for perfect web search - 100% accuracy"""
    prompt = f"""
    User wants to search the web. Extract the perfect search query from their request.
    
    User Request: "{query}"
    
    Provide ONLY the exact search terms needed for Google search. No explanations, no greetings, no extra words.
    
    Examples:
    - "I want you to find Tesla stock price" → tesla stock price
    - "Let's search about climate change effects" → climate change effects
    - "I want to watch Avengers Endgame movie" → Avengers Endgame movie
    - "Let's listen to Bohemian Rhapsody by Queen" → Bohemian Rhapsody Queen
    - "Find information about iPhone 15 reviews" → iPhone 15 reviews
    - "a car on a web browser" → car
    - "search a sport car on web browser" → sport car
    
    Search Query:"""
    
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 50,
                "temperature": 0.2
            },
            timeout=8
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_query = result['choices'][0]['message']['content'].strip()
            return ai_query
        else:
            return None
            
    except Exception as e:
        print(f"AI query refinement timeout - using fallback")
        return None

def is_direct_search_query(query):
    """Check if query explicitly contains search commands"""
    search_keywords = ['search', 'find', 'look up', 'look for', 'browse', 'google']
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in search_keywords)

def needs_ai_web_search(query):
    """Determine if query needs real-time info but doesn't explicitly say 'search'"""
    prompt = f"""
    Analyze if this query needs CURRENT/REAL-TIME information that requires web search.
    
    Query: "{query}"
    
    Reply ONLY with "YES" if it needs current info, or "NO" if it doesn't.
    
    NEEDS CURRENT INFO (YES):
    - "I want to check price of IBM" → YES (stock prices change)
    - "what's today's Australian news" → YES (news is current)
    - "current Bitcoin price" → YES (prices change)
    - "latest iPhone features" → YES (product info changes)
    - "who won the latest football match" → YES (sports results)
    - "what's the weather like" → YES (weather changes)
    - "Tesla stock price today" → YES (stock prices)
    
    DOESN'T NEED CURRENT INFO (NO):
    - "How are you" → NO (general conversation)
    - "Open calculator" → NO (app command)
    - "what is 2+2" → NO (basic math)
    - "tell me a joke" → NO (general AI capability)
    - "good morning" → NO (greeting)
    
    DECISION: Does this query require CURRENT/REAL-TIME information from the internet?
    """
    
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 10,
                "temperature": 0.1
            },
            timeout=8
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content'].strip().upper()
            return "YES" in ai_response
        else:
            return False
            
    except Exception as e:
        print(f"AI current info detection timeout - using fallback")
        return False

def get_mistral_web_search_response(query):
    """Use Mistral AI for real-time information - simplified approach"""
    try:
        print(f"🔍 Using Mistral AI for current info: '{query}'")
        
        # Use direct chat completions with web search instructions
        enhanced_prompt = f"""
        Please provide current, up-to-date information about: {query}
        
        If this requires current/real-time data (like stock prices, news, weather, sports results), 
        please indicate that you would need to search the web for the latest information.
        
        Query: {query}
        """
        
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": enhanced_prompt}],
                "max_tokens": 200,
                "temperature": 0.3
            },
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content'].strip()
            print(f"✅ Mistral response: {ai_response[:100]}...")
            return ai_response
        else:
            print(f"Mistral API failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Mistral web search error: {e}")
        return None

def extract_search_query_advanced(query):
    """Enhanced search query extraction with two-tier system - VIDEO DETECTION FIRST"""
    
    # First, check if this is a search-related query using AI
    print(f"🧠 AI analyzing query: '{query}'")
    
    is_search_query = is_search_related_query(query)
    
    if is_search_query:
        print("✅ AI detected: Search/Info query")
        
        # PRIORITY 1: Check if it's a simple information query (what is X, tell me about X)
        simple_info_patterns = [
            r'\bwhat\s+is\s+',
            r'\btell\s+me\s+(?:about\s+|the\s+information\s+about\s+)',
            r'\blet\s+me\s+know\s+(?:about\s+|the\s+information\s+about\s+)',
            r'\binformation\s+about\s+',
            r'\bwho\s+is\s+',
            r'\bhow\s+(?:does|do)\s+',
            r'\bwhere\s+is\s+',
            r'\bwhen\s+(?:was|is)\s+',
            r'\bwhy\s+(?:is|does)\s+',
        ]
        
        import re
        for pattern in simple_info_patterns:
            if re.search(pattern, query.lower()):
                print("🤖 Simple information query detected - using Mistral AI")
                return "MISTRAL_WEB_SEARCH"  # Use AI to answer directly
        
        # PRIORITY 2: Check if it's a VIDEO query (before other logic)
        if is_video_search_query(query):
            print("🎬 VIDEO SEARCH detected - extracting video search terms")
            # Get AI-refined search terms for video
            ai_refined_query = get_ai_refined_search_query(query)
            
            if ai_refined_query and len(ai_refined_query.strip()) > 0:
                print(f"🎯 Video search query: '{ai_refined_query}'")
                return ai_refined_query
            else:
                print("⚠️ AI video refinement failed, using basic extraction")
                # Fallback extraction for video
                return extract_video_terms(query)
        
        # PRIORITY 3: Check if it's a direct search (contains "search", "find", etc.)
        elif is_direct_search_query(query):
            print("🔍 Direct search detected - using browser")
            # Get AI-refined search terms for browser
            ai_refined_query = get_ai_refined_search_query(query)
            
            if ai_refined_query and len(ai_refined_query.strip()) > 0:
                print(f"🎯 AI refined query: '{ai_refined_query}'")
                return ai_refined_query
            else:
                print("⚠️ AI refinement failed, using regex fallback")
        
        # PRIORITY 4: Check if it needs real-time info (indirect search)
        elif needs_ai_web_search(query):
            print("🤖 Indirect search detected - using Mistral AI web search")
            return "MISTRAL_WEB_SEARCH"  # Special marker
        else:
            print("💬 Regular conversation query")
            return None
    else:
        print("🚫 AI detected: Not a search query")
        return None

def extract_video_terms(query):
    """Fallback video term extraction"""
    # Remove common video command words
    video_command_words = {'watch', 'video', 'videos', 'start', 'play', 'show', 'open', 'i', 'want', 'to', 'a', 'an', 'the'}
    
    words = query.lower().split()
    filtered_words = [word for word in words if word not in video_command_words and len(word) > 1]
    
    if filtered_words:
        return ' '.join(filtered_words)
    else:
        return "music video"  # Safe fallback
    
    # Fallback to regex-based extraction if AI fails
    query_lower = query.lower().strip()
    
    # Financial/Stock patterns - High priority
    financial_patterns = [
        r'(?:i\s+want\s+you\s+to\s+find\s+|find\s+|search\s+for\s+|look\s+for\s+)?(.+?)\s+(?:share\s+price|stock\s+price|price\s+share|stock\s+market)',
        r'(?:price\s+of\s+|stock\s+|share\s+)(.+?)(?:\s+share|\s+stock|$)',
        r'(?:i\s+want\s+you\s+to\s+find\s+|find\s+)?(.+?)\s+(?:market\s+price|trading\s+price|share\s+value)',
        r'(?:i\s+want\s+you\s+to\s+find\s+|find\s+)?(.+?)\s+price\s+share\s+price',  # Handle "tesla price share price"
    ]
    
    for pattern in financial_patterns:
        match = re.search(pattern, query_lower)
        if match:
            company = match.group(1).strip()
            # Clean company name from common prefixes
            company = re.sub(r'^(?:today\'s|current|latest|the|a|an)\s+', '', company)
            company = re.sub(r'^(?:i\s+want\s+you\s+to\s+find\s+|find\s+|search\s+for\s+)', '', company)
            return f"{company} stock price"
    
    # Search command extraction with smart filtering
    search_patterns = [
        # I want you to find patterns
        r'i\s+want\s+you\s+to\s+find\s+(.+?)(?:\s+on\s+(?:safari|browser|web|internet))?$',
        r'i\s+want\s+you\s+to\s+search\s+(?:for\s+)?(.+?)(?:\s+on\s+(?:safari|browser|web))?$',
        r'i\s+want\s+to\s+watch\s+(.+?)(?:\s+movie|\s+video)?(?:\s+on\s+(?:youtube|netflix))?$',
        r'let\'s\s+search\s+(?:it\s+up\s+)?(?:about\s+)?(.+?)(?:\s+on\s+(?:safari|browser|web))?$',
        r'let\'s\s+listen\s+(?:to\s+)?(.+?)(?:\s+song|\s+music)?$',
        
        # Direct search commands
        r'search\s+(?:for\s+|up\s+)?(.+?)(?:\s+on\s+(?:safari|browser|web|internet))?$',
        r'look\s+(?:for\s+|up\s+)?(.+?)(?:\s+on\s+(?:safari|browser|web|internet))?$',
        r'find\s+(?:me\s+)?(.+?)(?:\s+on\s+(?:safari|browser|web|internet))?$',
        
        # Can you / please patterns
        r'can\s+you\s+search\s+(?:for\s+|up\s+)?(.+?)(?:\s+on\s+(?:safari|browser|web))?$',
        r'please\s+search\s+(?:for\s+|up\s+)?(.+?)(?:\s+on\s+(?:safari|browser|web))?$',
        
        # Checkout patterns for web searches
        r'checkout\s+(.+?)(?:\s+on\s+(?:safari|browser|web|internet))?$',
        r'check\s+out\s+(.+?)(?:\s+on\s+(?:safari|browser|web|internet))?$',
        
        # Complex patterns with platform mentions
        r'search\s+(.+?)\s+on\s+(?:safari|browser|web)',
        r'(.+?)\s+on\s+(?:safari|browser|web|internet)',
    ]
    
    for pattern in search_patterns:
        match = re.search(pattern, query_lower)
        if match:
            search_term = match.group(1).strip()
            
            # Advanced cleaning - remove redundant words
            search_term = re.sub(r'\s+(?:on\s+(?:safari|browser|web|internet)|please|up)$', '', search_term)
            search_term = re.sub(r'^(?:a\s+|an\s+|the\s+)', '', search_term)  # Remove articles
            
            # Remove platform mentions that got mixed in
            search_term = re.sub(r'\s+(?:web\s+browser|browser|safari|internet)$', '', search_term)
            search_term = re.sub(r'\s+on\s+web\s+browser$', '', search_term)
            
            return search_term.strip()
    
    # Final fallback: Smart word filtering
    command_words = {
        'i', 'want', 'you', 'to', 'can', 'please', 'search', 'for', 'up', 'look', 'find', 'me', 
        'on', 'safari', 'browser', 'web', 'internet', 'website', 'online', 'let\'s', 'lets',
        'a', 'an', 'the', 'watch', 'listen'
    }
    
    words = query_lower.split()
    filtered_words = [word for word in words if word not in command_words]
    
    if filtered_words:
        result = ' '.join(filtered_words)
        # Final cleanup
        result = re.sub(r'\s+on\s+web\s+browser$', '', result)
        result = re.sub(r'\s+web\s+browser$', '', result)
        return result.strip()
    
    return None

def search_videos_in_youtube(search_query):
    """Search for videos directly in YouTube application"""
    try:
        clean_query = search_query.strip()
        encoded_query = urllib.parse.quote(clean_query)
        youtube_search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        
        print(f"🎬 Searching YouTube for: {clean_query}")
        
        # Try to open in YouTube app first
        youtube_apps = ['YouTube', 'Friendly Streaming', 'YouTube TV']
        app_opened = False
        
        for youtube_app in youtube_apps:
            try:
                subprocess.run(['open', '-a', youtube_app], check=True)
                app_opened = True
                print(f"📱 Opened {youtube_app}")
                
                # Wait and then open the search URL in the app
                time.sleep(2)
                webbrowser.open(youtube_search_url)
                break
            except subprocess.CalledProcessError:
                continue
        
        if not app_opened:
            # Fallback to Safari
            webbrowser.get('safari').open_new_tab(youtube_search_url)
            os.system("osascript -e 'tell application \"Safari\" to activate'")
            print("🌐 Opened YouTube in Safari")
        
        return True, f"Here are {clean_query} videos sir"
        
    except Exception as e:
        return False, f"Error searching YouTube: {e}"

def search_in_safari(search_query):
    """Open Safari and search for specific content"""
    try:
        clean_query = search_query.strip()
        encoded_query = urllib.parse.quote(clean_query)
        search_url = f"https://www.google.com/search?q={encoded_query}"
        
        print(f"🔍 Searching for: {clean_query}")
        
        # Open Safari with search
        webbrowser.get('safari').open_new_tab(search_url)
        
        # Bring Safari to front
        time.sleep(1)
        os.system("osascript -e 'tell application \"Safari\" to activate'")
        
        return True, f"Here you can see {clean_query} sir"
        
    except Exception as e:
        return False, f"Error searching in Safari: {e}"

def get_location_coordinates(location_name):
    """Get latitude and longitude coordinates for a location using AI"""
    prompt = f"""
    Get the exact latitude and longitude coordinates for: "{location_name}"
    
    Respond with ONLY the coordinates in this format: latitude,longitude
    
    Examples:
    - "Melbourne" → -37.8136,144.9631
    - "Sydney" → -33.8688,151.2093
    - "Brisbane" → -27.4698,153.0251
    - "Perth" → -31.9505,115.8605
    - "Adelaide" → -34.9285,138.6007
    - "Canberra" → -35.2809,149.1300
    - "Darwin" → -12.4634,130.8456
    - "Hobart" → -42.8821,147.3272
    - "Geelong" → -38.1499,144.3617
    - "Gold Coast" → -28.0167,153.4000
    - "London" → 51.5074,-0.1278
    - "New York" → 40.7128,-74.0060
    - "Tokyo" → 35.6762,139.6503
    
    Coordinates:"""
    
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 50,
                "temperature": 0.1
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            coords_text = result['choices'][0]['message']['content'].strip()
            
            # Parse the coordinates
            try:
                lat, lon = coords_text.split(',')
                return float(lat.strip()), float(lon.strip())
            except (ValueError, AttributeError):
                print(f"Failed to parse coordinates: {coords_text}")
                return None
        else:
            return None
            
    except Exception as e:
        print(f"AI coordinate lookup timeout - using fallback: {e}")
        # Fallback coordinates for major Australian cities
        fallback_coords = {
            'melbourne': (-37.8136, 144.9631),
            'sydney': (-33.8688, 151.2093),
            'brisbane': (-27.4698, 153.0251),
            'perth': (-31.9505, 115.8605),
            'adelaide': (-34.9285, 138.6007),
            'canberra': (-35.2809, 149.1300),
            'darwin': (-12.4634, 130.8456),
            'hobart': (-42.8821, 147.3272),
            'geelong': (-38.1499, 144.3617),
            'gold coast': (-28.0167, 153.4000)
        }
        
        location_lower = location_name.lower().strip()
        for city, coords in fallback_coords.items():
            if city in location_lower:
                return coords
        
        return None

def extract_location_from_weather_query(query):
    """Extract location from weather-related queries using AI and regex patterns"""
    
    # First try regex patterns for common weather query formats
    weather_patterns = [
        r'weather\s+(?:in|of|for|at)\s+(.+?)(?:\s+please|$)',
        r'(?:find\s+out\s+|check\s+|get\s+)?weather\s+(?:in|of|for|at)\s+(.+?)(?:\s+please|$)',
        r'what\'?s\s+the\s+weather\s+(?:like\s+)?(?:in|at|for)\s+(.+?)(?:\s+please|$)',
        r'how\'?s\s+the\s+weather\s+(?:in|at|for)\s+(.+?)(?:\s+please|$)',
        r'temperature\s+(?:in|of|at|for)\s+(.+?)(?:\s+please|$)',
        r'(?:tell\s+me\s+)?(?:the\s+)?weather\s+(?:forecast\s+)?(?:in|of|at|for)\s+(.+?)(?:\s+please|$)',
        r'(.+?)\s+weather(?:\s+please)?$',  # "Melbourne weather"
        r'weather\s+(.+?)(?:\s+today|now|please)?$'  # "weather Melbourne"
    ]
    
    query_lower = query.lower().strip()
    
    # Try regex patterns first for speed
    import re
    for pattern in weather_patterns:
        match = re.search(pattern, query_lower)
        if match:
            location = match.group(1).strip()
            # Clean up the location
            location = re.sub(r'^(?:the\s+|a\s+|an\s+)', '', location)  # Remove articles
            location = re.sub(r'\s+(?:please|today|now|currently)$', '', location)  # Remove time words
            if len(location) > 0 and not any(word in location for word in ['weather', 'temperature', 'forecast']):
                print(f"🌤️ REGEX: Extracted location '{location}' from weather query")
                return location.title()
    
    # If regex fails, use AI to extract location
    prompt = f"""
    Extract the location name from this weather query. Reply with ONLY the location name, nothing else.
    
    Query: "{query}"
    
    Examples:
    - "find out weather of Melbourne" → Melbourne
    - "what's the weather in Sydney today" → Sydney  
    - "check weather in New York" → New York
    - "Melbourne weather" → Melbourne
    - "weather in London please" → London
    - "how's the weather at Brisbane" → Brisbane
    
    If no location found, reply with: NONE
    
    Location:"""
    
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 20,
                "temperature": 0.1
            },
            timeout=8
        )
        
        if response.status_code == 200:
            result = response.json()
            location = result['choices'][0]['message']['content'].strip()
            
            if location.upper() != "NONE" and len(location) > 0:
                print(f"🌤️ AI: Extracted location '{location}' from weather query")
                return location
            else:
                print(f"🌤️ No location found in query: '{query}'")
                return None
        else:
            print(f"🌤️ AI extraction failed, no location found")
            return None
            
    except Exception as e:
        print(f"🌤️ AI location extraction timeout: {e}")
        return None

def get_web_url_for_app(app_name):
    """AI-powered web URL generation for applications not found locally"""
    prompt = f"""
    User wants to open "{app_name}" but it's not installed on their device.
    Provide the EXACT web URL to open this application/platform in a browser.
    
    App/Platform: "{app_name}"
    
    Respond with ONLY the URL, no explanations.
    
    Examples:
    - "Facebook" → https://www.facebook.com
    - "Spotify" → https://open.spotify.com
    - "Google Cloud" → https://console.cloud.google.com
    - "Instagram" → https://www.instagram.com
    - "Twitter" → https://twitter.com
    - "LinkedIn" → https://www.linkedin.com
    - "Discord" → https://discord.com/app
    - "Slack" → https://slack.com/signin
    - "Notion" → https://www.notion.so
    - "Figma" → https://www.figma.com
    
    URL:"""
    
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 50,
                "temperature": 0.1
            },
            timeout=8
        )
        
        if response.status_code == 200:
            result = response.json()
            url = result['choices'][0]['message']['content'].strip()
            # Clean the URL if it has extra text
            if 'http' in url:
                # Extract just the URL part
                import re
                url_match = re.search(r'https?://[^\s]+', url)
                if url_match:
                    return url_match.group(0)
            return url
        else:
            return None
            
    except Exception as e:
        print(f"AI URL generation timeout - using fallback")
        return None

def open_application(app_name):
    """Enhanced application opening with intelligent web fallback"""
    # User's local applications - prioritize these over web versions
    app_mappings = {
        # System apps
        'safari': 'Safari',
        'chrome': 'Google Chrome',
        'firefox': 'Firefox',
        'terminal': 'Terminal',
        'finder': 'Finder',
        'calculator': 'Calculator',
        'calendar': 'Calendar',
        'notes': 'Notes',
        'music': 'Music',
        'mail': 'Mail',
        'messages': 'Messages',
        
        # User's installed applications (LOCAL PRIORITY) - Made more specific
        'chatgpt': 'ChatGPT',
        'chat gpt': 'ChatGPT',
        'chatgpt app': 'ChatGPT',
        'gemini': 'Gemini',
        'google gemini': 'Gemini',
        'gemini app': 'Gemini',
        'cursor': 'Cursor',
        'cursor ai': 'Cursor',
        'gmail': 'Gmail',
        'microsoft word': 'Microsoft Word',
        'ms word': 'Microsoft Word',
        'metamask': 'MetaMask',
        'meta mask': 'MetaMask',
        'notebooklm': 'NotebookLM',
        'notebook lm': 'NotebookLM',
        'docker': 'Docker',
        'capcut': 'CapCut',
        'cap cut': 'CapCut',
        'grok': 'Grok',
        'grok ai': 'Grok',
        'groq': 'Grok',
        'grog': 'Grok',
        
        # College/Education specific - EXACT MATCH REQUIRED
        'mit ams': 'WEB_AMS',  # Special marker for MIT AMS
        'ams': 'WEB_AMS',  # Only when context suggests college
        
        # Other common apps
        'youtube': 'YouTube',
        'whatsapp': 'WhatsApp',
        'vscode': 'Visual Studio Code',
        'code': 'Visual Studio Code',
        'spotify': 'Spotify',
        'zoom': 'Zoom'
    }
    
    # Direct web URL mappings for apps NOT installed locally
    # Note: User's local apps (ChatGPT, Gemini, Cursor, etc.) are excluded from web URLs
    web_app_urls = {
        'facebook': 'https://www.facebook.com',
        'instagram': 'https://www.instagram.com',
        'twitter': 'https://twitter.com',
        'linkedin': 'https://www.linkedin.com',
        'discord': 'https://discord.com/app',
        'slack': 'https://slack.com/signin',
        'notion': 'https://www.notion.so',
        'figma': 'https://www.figma.com',
        'github': 'https://github.com',
        'dropbox': 'https://www.dropbox.com',
        'trello': 'https://trello.com',
        'google cloud': 'https://console.cloud.google.com',
        'google cloud platform': 'https://console.cloud.google.com',
        'booking': 'https://www.booking.com',
        'booking.com': 'https://www.booking.com',
        'spotify': 'https://open.spotify.com',
        'mit': 'https://www.mit.edu',
        'mit AMS': 'https://ams.mit.edu.au/Login/Index?ReturnUrl=%2fStudent%2fDashboard', 
        'moodle': 'https://moodle.mit.edu.au/login/index.php'
        # Removed: spotify, chatgpt, gemini, cursor, gmail, docker - these are installed locally
    }
    
    app_name_lower = app_name.lower().strip()
    
    try:
        # Special handling for YouTube with multiple app attempts
        if 'youtube' in app_name_lower:
            youtube_apps = ['YouTube', 'Friendly Streaming', 'YouTube TV']
            for youtube_app in youtube_apps:
                try:
                    subprocess.run(['open', '-a', youtube_app], check=True)
                    return True, f"Opened {youtube_app}"
                except subprocess.CalledProcessError:
                    continue
            # Fallback to Safari
            webbrowser.get('safari').open_new_tab('https://www.youtube.com')
            os.system("osascript -e 'tell application \"Safari\" to activate'")
            return True, "Opened YouTube in Safari"
        
        # Special handling for Gmail with direct app attempt first
        elif 'gmail' in app_name_lower:
            # Try to open Gmail as a direct app first (Add to Dock apps)
            gmail_app_attempts = ['Gmail', 'Gmail - Google', 'Mail']
            
            for gmail_app in gmail_app_attempts:
                try:
                    subprocess.run(['open', '-a', gmail_app], check=True)
                    return True, f"Opened {gmail_app}"
                except subprocess.CalledProcessError:
                    continue
            
            # If no direct app found, open in Safari (fallback)
            webbrowser.get('safari').open_new_tab('https://mail.google.com/mail/u/0/#inbox')
            os.system("osascript -e 'tell application \"Safari\" to activate'")
            return True, "Opened Gmail in Safari"
        
        # Regular app opening for other applications
        else:
            # Smart matching for user's local apps with multiple name variations
            target_app = None
            
            # Enhanced matching for local apps - EXACT MATCH FIRST
            for key, value in app_mappings.items():
                if key == app_name_lower:  # Exact match first
                    target_app = value
                    print(f"🎯 Exact match found: '{app_name}' → '{target_app}'")
                    break
            
            # If no exact match, try contains matching but exclude problematic cases
            if not target_app:
                for key, value in app_mappings.items():
                    if key in app_name_lower and key != 'mit':  # Avoid "mit" matching in "mit ams"
                        # Special case: Don't match "word" if it's part of "mit ams" context
                        if key == 'word' and ('mit' in app_name_lower or 'ams' in app_name_lower):
                            continue
                        # CRITICAL FIX: Don't match "ai" alone - it's too generic
                        if key == 'ai' or key == 'openai':
                            # Only match if it's a clear app opening request, not information request
                            if not any(info_word in app_name_lower for info_word in ['news', 'about', 'information', 'latest', 'find', 'search']):
                                target_app = value
                                print(f"🎯 Contains match found: '{app_name}' → '{target_app}'")
                                break
                        else:
                            target_app = value
                            print(f"🎯 Contains match found: '{app_name}' → '{target_app}'")
                            break
            
            # If no contains match, try partial matching for compound names (more careful)
            if not target_app:
                for key, value in app_mappings.items():
                    key_words = key.split()
                    app_words = app_name_lower.split()
                    
                    # Avoid matching "mit" alone when user says "mit ams"
                    if key == 'word' and any(word in ['mit', 'ams'] for word in app_words):
                        continue
                        
                    if any(word in app_words for word in key_words):
                        target_app = value
                        print(f"🎯 Partial match found: '{app_name}' → '{target_app}'")
                        break
            
            # Handle special WEB_AMS marker
            if target_app == 'WEB_AMS':
                print(f"🎓 Opening MIT AMS in web browser")
                webbrowser.get('safari').open_new_tab('https://ams.mit.edu.au/Login/Index?ReturnUrl=%2fStudent%2fDashboard')
                time.sleep(1)
                os.system("osascript -e 'tell application \"Safari\" to activate'")
                return True, "Opened MIT AMS in Safari"
            
            # Fallback to title case
            if not target_app:
                target_app = app_name.title()
            
            # Try to open the local application first
            try:
                subprocess.run(['open', '-a', target_app], check=True)
                print(f"✅ Successfully opened local app: {target_app}")
                return True, f"Opened {target_app}"
            except subprocess.CalledProcessError:
                # App not found locally - try web version ONLY if not in user's local app list
                print(f"📱 App '{app_name}' not found locally, checking web version...")
                
                # Check if this is one of user's local apps that should NOT open in browser
                user_local_apps = ['chatgpt', 'openai', 'chat gpt', 'open ai', 'gemini', 'google ai', 
                                 'cursor', 'cursor ai', 'gmail', 'microsoft word', 'word', 'metamask', 
                                 'notebooklm', 'notebook lm', 'docker', 'capcut', 'cap cut']
                
                is_local_app = any(local_app in app_name_lower for local_app in user_local_apps)
                
                if is_local_app:
                    print(f"⚠️ '{app_name}' should be installed locally but wasn't found")
                    return False, f"Could not find {app_name}. Please check if it's installed correctly."
                
                # For non-local apps, try web version
                web_url = None
                for web_app, url in web_app_urls.items():
                    if web_app in app_name_lower:
                        web_url = url
                        break
                
                # If no direct mapping, use AI to get the URL
                if not web_url:
                    print(f"🤖 AI generating web URL for: {app_name}")
                    web_url = get_web_url_for_app(app_name)
                
                if web_url:
                    print(f"🌐 Opening web version: {web_url}")
                    webbrowser.get('safari').open_new_tab(web_url)
                    time.sleep(1)
                    os.system("osascript -e 'tell application \"Safari\" to activate'")
                    return True, f"Opened {app_name} in Safari"
                else:
                    return False, f"Could not find {app_name} locally or generate web URL"
        
    except Exception as e:
        return False, f"Error opening {app_name}: {e}"

def close_application(app_name):
    """Close specific applications by name with enhanced local app support"""
    app_mappings = {
        # System apps
        'safari': 'Safari',
        'chrome': 'Google Chrome',
        'firefox': 'Firefox',
        'terminal': 'Terminal',
        'finder': 'Finder',
        'calculator': 'Calculator',
        'calendar': 'Calendar',
        'notes': 'Notes',
        'music': 'Music',
        'mail': 'Mail',  # Built-in Mail app
        'messages': 'Messages',
        
        # User's installed applications (LOCAL PRIORITY)
        'chatgpt': 'ChatGPT',
        'chat gpt': 'ChatGPT',
        'chat gbt': 'ChatGPT',
        'jet gpt': 'ChatGPT',
        'gpt': 'ChatGPT',
        'openai': 'ChatGPT',
        'open ai': 'ChatGPT',
        'gemini': 'Gemini',
        'google ai': 'Gemini',
        'google gemini': 'Gemini',
        'cursor': 'Cursor',
        'cursor ai': 'Cursor',
        'gmail': 'Gmail',  # Gmail app (installed separately)
        'g mail': 'Gmail',
        'google mail': 'Gmail',
        'microsoft word': 'Microsoft Word',
        'word': 'Microsoft Word',
        'ms word': 'Microsoft Word',
        'metamask': 'MetaMask',
        'meta mask': 'MetaMask',
        'notebookllm': 'NotebookLLM',
        'notebook llm': 'NotebookLLM',
        'docker': 'Docker',
        'capcut': 'CapCut',
        'cap cut': 'CapCut',
        
        # Other common apps
        'youtube': ['YouTube', 'Friendly Streaming', 'YouTube TV'],
        'whatsapp': 'WhatsApp',
        'vscode': 'Visual Studio Code',
        'code': 'Visual Studio Code',
        'spotify': 'Spotify',
        'zoom': 'Zoom'
    }
    
    app_name_lower = app_name.lower().strip()
    
    try:
        if 'youtube' in app_name_lower:
            # Try to close all possible YouTube apps
            youtube_apps = ['YouTube', 'Friendly Streaming', 'YouTube TV']
            for youtube_app in youtube_apps:
                os.system(f"osascript -e 'quit app \"{youtube_app}\"'")
            return True, "Closed YouTube applications"
        
        # Smart matching for local apps (same logic as opening)
        target_app = None
        
        # Enhanced matching for local apps - EXACT MATCH FIRST
        for key, value in app_mappings.items():
            if isinstance(value, list):
                continue  # Skip YouTube (handled above)
            if key == app_name_lower:  # Exact match first
                target_app = value
                print(f"🎯 Exact match found to close: '{app_name}' → '{target_app}'")
                break
        
        # If no exact match, try contains matching
        if not target_app:
            for key, value in app_mappings.items():
                if isinstance(value, list):
                    continue  # Skip YouTube (handled above)
                if key in app_name_lower and key != 'mail':  # Don't match 'mail' for 'gmail'
                    target_app = value
                    print(f"🎯 Contains match found to close: '{app_name}' → '{target_app}'")
                    break
        
        # If no exact match, try partial matching for compound names
        if not target_app:
            for key, value in app_mappings.items():
                if isinstance(value, list):
                    continue  # Skip YouTube
                if any(word in app_name_lower for word in key.split()):
                    target_app = value
                    print(f"🎯 Partial match found to close: '{app_name}' → '{target_app}'")
                    break
        
        # Fallback to title case
        if not target_app:
            target_app = app_name.title()
        
        # Close the application
        os.system(f"osascript -e 'quit app \"{target_app}\"'")
        print(f"✅ Successfully closed: {target_app}")
        return True, f"Closed {target_app}"
        
    except Exception as e:
        return False, f"Error closing {app_name}: {e}"

def execute_system_command(command_type, query, ai_handler):
    """Execute system commands with improved accuracy and video detection"""
    start_time = time.time()
    
    if command_type == 'search_safari':
        # Extract what to search for with improved accuracy
        search_query = extract_search_query_advanced(query)
        
        if search_query == "MISTRAL_WEB_SEARCH":
            # Use Mistral AI web search for indirect queries
            print(f"🤖 Using Mistral AI web search for: '{query}'")
            web_response = get_mistral_web_search_response(query)
            
            response_time = time.time() - start_time
            
            if web_response:
                speak(web_response)
                log_conversation(query, web_response, response_time, "Mistral AI Web Search", "AI Web Search")
            else:
                fallback_response = "I'm having trouble getting that information right now sir. Let me try a regular search for you."
                speak(fallback_response)
                # Fallback to regular browser search
                webbrowser.get('safari').open_new_tab('https://www.google.com')
                log_conversation(query, fallback_response, response_time, "Mistral AI Fallback")
        
        elif search_query:
            # Use AI to determine if this is a video search with 100% accuracy
            print(f"🤖 AI analyzing search type for: '{query}'")
            is_video_search = is_video_search_query(query)
            
            if is_video_search:
                # Search in YouTube for videos
                success, message = search_videos_in_youtube(search_query)
                query_type = "YouTube Video Search"
                print(f"🎬 AI detected: Video search - using YouTube")
            else:
                # Regular web search
                success, message = search_in_safari(search_query)
                query_type = "Web Search"
                print(f"🔍 AI detected: Web search - using Safari")
            
            response_time = time.time() - start_time
            
            if success:
                speak(message)
                log_conversation(f"Search: {search_query}", message, response_time, query_type, search_query)
            else:
                speak("I had trouble searching sir. Let me open Safari for you.")
                webbrowser.get('safari').open_new_tab('https://www.google.com')
        else:
            speak("I'll open Safari for you sir. What would you like me to search for?")
            webbrowser.get('safari').open_new_tab('https://www.google.com')
            response_time = time.time() - start_time
            log_conversation(query, "Opened Safari for search", response_time, "Fallback Search")
        
    elif command_type in ['open_safari', 'open_app', 'open_youtube', 'open_gmail']:
        # Enhanced app name extraction
        app_name = 'safari'  # default
        
        if 'youtube' in query.lower():
            app_name = 'youtube'
        elif 'gmail' in query.lower():
            app_name = 'gmail'
        elif 'calculator' in query.lower():
            app_name = 'calculator'
        else:
            # Smart app name extraction
            query_lower = query.lower()
            words = query_lower.split()
            
            # Remove common words and find the main app name
            skip_words = {'open', 'start', 'launch', 'let\'s', 'lets', 'a', 'an', 'the', 'application', 'app', 'website', 'platform'}
            
            # Look for app name after command words
            for i, word in enumerate(words):
                if word in ['open', 'start', 'launch']:
                    # Get remaining words after the command
                    remaining_words = words[i+1:]
                    # Filter out skip words and combine meaningful words
                    app_words = []
                    for w in remaining_words:
                        if w not in skip_words and len(w) > 1:
                            app_words.append(w)
                    
                    if app_words:
                        app_name = ' '.join(app_words[:3])  # Take up to 3 words
                        break
            
            # If no pattern found, extract the last few meaningful words
            if app_name == 'safari':
                meaningful_words = [w for w in words if w not in skip_words and len(w) > 1]
                if meaningful_words:
                    app_name = ' '.join(meaningful_words[-2:])  # Take last 2 words
        
        success, message = open_application(app_name)
        if success:
            speak(f"Done sir, {message.lower()}")
            log_conversation(query, message)
        else:
            speak("I had trouble opening that application sir.")
            log_conversation(query, f"Error: {message}")
        
    elif command_type in ['close_safari', 'close_app', 'close_youtube']:
        # Enhanced app name extraction for closing
        app_name = 'safari'  # default
        
        if 'youtube' in query.lower():
            app_name = 'youtube'
        elif 'gmail' in query.lower():
            app_name = 'gmail'  # Now properly handles Gmail closing
        else:
            # Smart app name extraction for closing
            query_lower = query.lower()
            words = query_lower.split()
            
            # Remove common words and find the main app name
            skip_words = {'close', 'quit', 'exit', 'turn', 'off', 'shut', 'down', 'stop', 'kill', 'end', 
                         'let\'s', 'lets', 'a', 'an', 'the', 'application', 'app', 'please'}
            
            # Look for app name after command words
            close_commands = ['close', 'quit', 'exit', 'turn', 'shut', 'stop', 'kill', 'end']
            for i, word in enumerate(words):
                if word in close_commands:
                    # Get remaining words after the command
                    remaining_words = words[i+1:]
                    # Filter out skip words and combine meaningful words
                    app_words = []
                    for w in remaining_words:
                        if w not in skip_words and len(w) > 1:
                            app_words.append(w)
                    
                    if app_words:
                        app_name = ' '.join(app_words[:3])  # Take up to 3 words
                        break
            
            # If no pattern found, extract the last few meaningful words
            if app_name == 'safari':
                meaningful_words = [w for w in words if w not in skip_words and len(w) > 1]
                if meaningful_words:
                    app_name = ' '.join(meaningful_words[-2:])  # Take last 2 words
        
        success, message = close_application(app_name)
        if success:
            speak(f"Done sir, {message.lower()}")
            log_conversation(query, message)
        else:
            speak("I had trouble closing that application sir.")
            log_conversation(query, f"Error: {message}")
    
    elif command_type == 'weather_query':
        # Extract location from the original query
        location_query = extract_location_from_weather_query(query)
        
        if location_query:
            try:
                # Get coordinates for the location using AI
                coords = get_location_coordinates(location_query)
                
                if coords:
                    lat, lon = coords
                    # Use Open-Meteo API for accurate weather data
                    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code&timezone=auto"
                    
                    response = requests.get(weather_url, timeout=10)
                    weather_data = response.json()
                    
                    current = weather_data['current']
                    temperature = current['temperature_2m']
                    feels_like = current['apparent_temperature']
                    humidity = current['relative_humidity_2m']
                    precipitation = current['precipitation']
                    
                    # Create detailed weather response
                    weather_response = f"In {location_query}, it's {temperature}°C and feels like {feels_like}°C. Humidity is {humidity}%"
                    
                    if precipitation > 0:
                        weather_response += f" with {precipitation}mm of precipitation"
                    
                    weather_response += " sir."
                    
                    speak(weather_response)
                    log_conversation(f"Weather in {location_query}", weather_response)
                else:
                    error_response = f"I couldn't find the location {location_query}. Could you try a different location sir?"
                    speak(error_response)
                    log_conversation(f"Weather error: {location_query}", error_response)
                    
            except Exception as e:
                print(f"Weather API error: {e}")
                error_response = "I'm having trouble getting the weather information sir. Please try again."
                speak(error_response)
                log_conversation(query, error_response)
        else:
            # Fallback: ask for location if not found in query
            speak("Which area would you like me to check sir?")
            result = recognition()
            if result[0] is not None:
                fallback_location, _ = result
                try:
                    coords = get_location_coordinates(fallback_location)
                    
                    if coords:
                        lat, lon = coords
                        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code&timezone=auto"
                        
                        response = requests.get(weather_url, timeout=10)
                        weather_data = response.json()
                        
                        current = weather_data['current']
                        temperature = current['temperature_2m']
                        feels_like = current['apparent_temperature']
                        humidity = current['relative_humidity_2m']
                        precipitation = current['precipitation']
                        
                        weather_response = f"In {fallback_location}, it's {temperature}°C and feels like {feels_like}°C. Humidity is {humidity}%"
                        
                        if precipitation > 0:
                            weather_response += f" with {precipitation}mm of precipitation"
                        
                        weather_response += " sir."
                        
                        speak(weather_response)
                        log_conversation(f"Weather in {fallback_location}", weather_response)
                    else:
                        error_response = f"I couldn't find the location {fallback_location}. Could you try a different location sir?"
                        speak(error_response)
                        log_conversation(f"Weather error: {fallback_location}", error_response)
                        
                except Exception as e:
                    print(f"Weather API error: {e}")
                    error_response = "I'm having trouble getting the weather information sir. Please try again."
                    speak(error_response)
                    log_conversation(query, error_response)
    
    elif command_type == 'goodbye':
        response = "See you next time sir. Have a great day!"
        speak(response)
        log_conversation(query, response)
        return True  # Signal to exit
        
    return False  # Continue running

class OptimizedSyraHandler(EdithAIHandler):
    """Optimized version of AI handler with speed improvements and casual personality"""
    
    def __init__(self, api_key):
        super().__init__(api_key)
        self.mistral_config.max_tokens = 120  # Even shorter for speed
        self.mistral_config.temperature = 0.5  # More consistent responses
    
    def get_ai_response(self, user_input, language='en'):
        """Optimized AI response with speed improvements and casual vibes"""
        
        # Quick casual responses for simple interactions
        casual_responses = {
            'hello': "Hey boss! What's up?",
            'hi': "Hi there! What can I do for ya?",
            'hey': "Hey! What's going on?",
            'good day': "Morning boss! Ready to get stuff done?",
            'good evening': "Evening! How's it going?",
            'good night': "Night boss! Sleep well!",
            'how are you': "I'm doing great! Just vibing and ready to help. How about you?",
            'whats up': "Just chilling and ready to help! What do you need?",
            'sup': "Not much! Just waiting for you to give me something cool to do!",
            'thanks': "No worries boss! Happy to help anytime!",
            'thank you': "You got it! That's what I'm here for!",
            'nice': "Right? Glad we're on the same page!",
            'cool': "Yeah! Pretty sweet, right?",
            'awesome': "I know, right? Always here when you need me!",
        }
        
        # Check for quick casual responses first
        user_lower = user_input.lower().strip()
        for trigger, response in casual_responses.items():
            if trigger in user_lower and len(user_lower.split()) <= 5:
                return {
                    'ai_response': response,
                    'system_command': self.detect_system_command(user_input),
                    'original_query': user_input,
                    'english_query': user_input
                }
        
        # For longer queries, use the full AI system
        return super().get_ai_response(user_input, language)

def main():
    # Check microphone permission
    if not check_microphone_permission():
        speak("I need microphone access to work properly.")
        sys.exit(1)
    
    # Initialize AI handler
    print("🤖 Initializing SYRA Final Version...")
    try:
        ai_handler = OptimizedSyraHandler(MISTRAL_API_KEY)
        translator = TranslationHandler()
        timeout_manager = TimeoutManager()
        print("✅ SYRA Final Version ready!")
        
        # Initialize conversation log
        with open(CONVERSATION_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"SYRA FINAL SESSION: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n")
            
    except Exception as e:
        print(f"❌ Error initializing SYRA: {e}")
        speak("I'm having trouble starting my system.")
        sys.exit(1)
    
    # Welcome message - More casual and friendly
    welcome_messages = [
        "Hey boss! SYRA here and ready to roll. What's up?",
        "What's good boss! I'm all set to help with searches, apps, or just chat. What do you need?",
        "Hey there! Your AI buddy SYRA is online and ready. What can we get done today?",
        "Good day boss! Saira here and pumped to help. What's the plan?",
        "Yo! SYRA back in action. Ready to search stuff, control apps, or just vibe. What's going on?"
    ]
    
    welcome_msg = random.choice(welcome_messages)
    speak(welcome_msg)
    log_conversation("SESSION_START", welcome_msg)
    
    print("🎙️ SYRA Final is listening... (Enhanced automation)")
    
    while True:
        # Get voice input
        result = recognition()
        if result[0] is None:
            # Handle timeout intelligently
            timeout_manager.increment_failure()
            
            # Check if we should exit
            if timeout_manager.should_exit():
                timeout_response = timeout_manager.get_timeout_response(conversation_context)
                speak(timeout_response)
                log_conversation("TIMEOUT_EXIT", timeout_response)
                print("👋 SYRA exiting gracefully due to user inactivity...")
                break
            
            # Get progressive timeout response
            timeout_response = timeout_manager.get_timeout_response(conversation_context)
            speak(timeout_response)
            continue
            
        query, detect_language = result
        
        # Reset timeout counter on successful recognition
        timeout_manager.reset()
        
        # Check for immediate disengagement signals
        if detect_user_disengagement(query):
            farewell = ["No worries, let's take a break. Feel free to call me anytime you need assistance. Have a great day sir!",
                        "Alright, I'm here whenever you need me. Just say the word and I'll be ready to help. Take care sir!",
                        "Got it, I'll be right here when you need me. Don't hesitate to call on me again. Have a good one sir!"]
            farewell = random.choice(farewell)
            speak(farewell)
            log_conversation(query, farewell)
            print("👋 SYRA exiting gracefully due to user request...")
            break
        
        # Handle Hindi input
        if detect_language == 'hi':
            english_query = translator.translate_text(query, src='hi', dest='en')
            print(f"Translated: {english_query}")
            processed_query = english_query
        else:
            processed_query = query
        
        # Use the enhanced AI handler's system command detection
        ai_result = ai_handler.get_ai_response(processed_query, language='en')
        
        # Clean the AI response
        clean_response = clean_markdown_response(ai_result['ai_response'])
        
        # Check if it's a system command using the ENHANCED detection
        if ai_result['system_command']:
            print(f"🔧 System command: {ai_result['system_command']}")
            
            should_exit = execute_system_command(
                ai_result['system_command'], 
                processed_query,
                ai_handler
            )
            
            if should_exit:
                break
            # Track system command context too
            update_conversation_context(query, "System command executed")
        else:
            # Regular AI conversation
            speak(clean_response)
            log_conversation(query, clean_response)
            # Track conversation context
            update_conversation_context(query, clean_response)

if __name__ == '__main__':
    main()
