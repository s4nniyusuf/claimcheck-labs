import os

from dotenv import load_dotenv
from groq import Groq


def load_api_key():
    load_dotenv() 
    api_key = os.getenv("GROQ_API_KEY")
    return api_key


def extract_sellers_claim_from_description(text):
  client = Groq(
      api_key=load_api_key(),
  )

  prompt = f"""
    Extract all factual claims from this product description: {text}.
    A claim is any statement describing a feature, quality, or benefit.
    Return **only** a JSON list, nothing else. Each item must have:
      - "claim": the claim text
      - "aspect": either "feature", "benefit", or "quality"
    Do not include any explanations or extra text.
    """
    
  try:
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-3.3-70b-versatile",
    )
    claims_jsons = chat_completion.choices[0].message.content
    return claims_jsons

  except Exception as e:
    print(f"Error extracting claims {e}")