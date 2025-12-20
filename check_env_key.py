
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL")

print(f"GROQ_API_KEY present: {bool(key)}")
if key:
    print(f"Key length: {len(key)}")
    print(f"Key prefix: {key[:5]}...")
print(f"GROQ_MODEL: {model}")
