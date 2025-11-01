# utils/ai_api.py
from openai import OpenAI
import os

# Try to load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("[❌] Warning: GROQ_API_KEY not found in environment variables")
    api_key = "dummy_key"  # tránh client lỗi sớm

client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1",
)

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

def ask_mistral(
    user_input: str,
    role: str = "book advisor",
    context: list | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """
    Gọi Groq Chat Completions có hỗ trợ:
      - role tuỳ biến -> đẩy vào system prompt
      - context: list[{'role': 'user|assistant|system', 'content': '...'}]
    """
    if not api_key or api_key == "dummy_key":
        print("[❌] GROQ_API_KEY not configured properly")
        return "Sorry, the AI service is not configured. Please set your GROQ_API_KEY environment variable."

    # Build messages
    messages = [
        {
            "role": "system",
            "content": f"You are a {role}. Be helpful, concise and professional in your responses.",
        }
    ]

    # Nhận context (lấy tối đa 12 msg gần nhất, lọc role hợp lệ)
    if context and isinstance(context, list):
        for m in context[-12:]:
            if isinstance(m, dict):
                r = m.get("role")
                c = m.get("content")
                if r in ("system", "user", "assistant") and c:
                    messages.append({"role": r, "content": c})
            # (tuỳ chọn) nếu FE gửi plain string, coi như user
            elif isinstance(m, str) and m.strip():
                messages.append({"role": "user", "content": m.strip()})

    # Tin nhắn hiện tại của user
    messages.append({"role": "user", "content": user_input})

    try:
        resp = client.chat.completions.create(
            model=model or DEFAULT_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        reply = resp.choices[0].message.content
        print("[✔] Groq reply:", reply)
        return reply
    except Exception as e:
        print("[❌] Groq API error:", str(e))
        return "Sorry, I could not respond at the moment."


# Back-compat: giữ tên hàm cũ nếu nơi khác đang import
def ask_mistral_with_custom_role(user_input: str, custom_role: str, context: list | None = None) -> str:
    return ask_mistral(user_input=user_input, role=custom_role, context=context)
