import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(r"c:\Users\A\OneDrive\Documents\Codex hackathon\.env")

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("Error: OPENAI_API_KEY not found in .env file.")
else:
    print(f"API Key exists: {api_key[:10]}...")
    client = OpenAI(api_key=api_key)
    
    # List models to verify connectivity without model-specific param issues
    try:
        print("1. Testing basic connectivity by listing models...")
        models = client.models.list()
        print("Success! The API key is valid and can list models.")
        
        # Now try to test a simple chat completion with gpt-4o-mini
        print("\n2. Testing chat completion with 'gpt-4o-mini'...")
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hi"}],
                max_completion_tokens=10 # Using more modern param name
            )
            print("Success! Chat completion works with 'gpt-4o-mini'.")
            print(f"Response: {response.choices[0].message.content}")
        except Exception as e:
            print(f"Chat completion with 'gpt-4o-mini' failed: {e}")

        # Now try the user's specific model from .env if it's there
        env_model = os.getenv("OPENAI_MODEL")
        if env_model:
            print(f"\n3. Testing with model specified in .env: '{env_model}'...")
            try:
                # O1/GPT-5 (if it existed) use completions slightly differently
                # Removing tokens to be safe
                response = client.chat.completions.create(
                    model=env_model,
                    messages=[{"role": "user", "content": "Hi"}],
                    max_completion_tokens=10
                )
                print(f"Success! Model '{env_model}' is working.")
            except Exception as e:
                print(f"Model '{env_model}' failed: {e}")
                
    except Exception as e:
        print(f"Failed to connect to OpenAI API: {e}")
