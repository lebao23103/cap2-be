from openai import OpenAI
import os

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Get API key from environment
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("[❌] Warning: GROQ_API_KEY not found in environment variables")
    api_key = "dummy_key"  # Prevent OpenAI client from failing

client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1"
)

def ask_mistral(user_input):
    if not api_key or api_key == "dummy_key":
        print("[❌] GROQ_API_KEY not configured properly")
        return "Sorry, the AI service is not configured. Please set your GROQ_API_KEY environment variable."
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            # model="mistral-7b-instruct-v0.1",  # Uncomment if you want to use the smaller model
            messages=[
                {"role": "system", "content": "You are a helpful book advisor who recommends books based on the user's interests, like a personal reading consultant."},
                {"role": "user", "content": user_input}
            ],
            temperature=0.7,
            max_tokens=2048
        )
        reply = response.choices[0].message.content
        print("[✔] Phản hồi từ Groq:", reply)
        return reply
    except Exception as e:
        print("[❌] Lỗi gọi Groq API:", str(e))
        return "Sorry, I could not respond at the moment."
