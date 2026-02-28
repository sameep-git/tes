import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

# We initialize the client using the GEMINI_API_KEY from the environment
client = genai.Client() if os.getenv("GEMINI_API_KEY") else None

def test_genai_call(prompt: str) -> str:
    """Basic wrapper to call Gemini, mainly used for testing setup."""
    if not client:
        return "GEMINI_API_KEY not found in environment."
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    return response.text