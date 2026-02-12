import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

def test_connection():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found in .env file.")
        return

    print(f"🚀 Testing Anthropic API with key: {api_key[:8]}...{api_key[-4:]}")
    
    try:
        client = Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=20,
            messages=[
                {"role": "user", "content": "Hello Claude, confirm connection."}
            ]
        )
        print(f"✅ Response from Claude: {message.content[0].text}")
    except Exception as e:
        print(f"❌ API Call Failed: {e}")

if __name__ == "__main__":
    test_connection()
