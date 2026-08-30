import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import Optional


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found. Check your .env file."
    )


client = genai.Client(api_key=api_key)


class NegotiationItem(BaseModel):
    item_name: str


class NegotiationRequest(BaseModel):
    intent: str
    requested_price: Optional[float] = None
    requested_discount: Optional[float] = None
    items: list[NegotiationItem]


def extract_negotiation_request(message):

    prompt = f"""
You are an AI shopping negotiation assistant.

Analyze the customer's message.

Customer message:
"{message}"

Extract:
1. Whether the customer is negotiating.
2. The total price they want, if mentioned.
3. The discount they want, if mentioned.
4. The products they mention.

Rules:
- intent must be NEGOTIATE or OTHER.
- requested_price is the total amount the customer wants to pay.
- requested_discount is the discount amount requested.
- Use null when the customer does not provide a value.
- Only include products explicitly mentioned by the customer.
- Every product MUST use the field "item_name".
- Do not invent products, prices, quantities, or discounts.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=NegotiationRequest
        )
    )

    return NegotiationRequest.model_validate_json(
        response.text
    )