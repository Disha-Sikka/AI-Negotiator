import os
import json

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found. Check your .env file."
    )

client = genai.Client(api_key=api_key)


def extract_negotiation_request(message):

    prompt = f"""
You are an AI shopping negotiation assistant.

Analyze the customer's message and extract their negotiation request.

Customer message:
"{message}"

Rules:
- intent must be either NEGOTIATE or OTHER.
- requested_price means the total price the customer wants to pay.
- requested_discount means the total discount the customer is asking for.
- If the customer doesn't mention a price, use null.
- If the customer doesn't mention a discount, use null.
- quantity should only be included if the customer explicitly mentions a quantity.
- Do not invent values.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    return json.loads(response.text)