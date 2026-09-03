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
    quantity: int = 1


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

1. Customer intent.
2. The total price they want, if mentioned.
3. The discount they want, if mentioned.
4. The products they mention.
5. The quantity requested for each product.

Quantity rules:

- If the customer explicitly mentions a quantity, extract it.
- If no quantity is mentioned, use quantity = 1.
- Do not invent quantities.
- Quantity must be a positive integer.

Examples:
Customer: "I'll take 5 USB-C cables for ₹3000."

→ intent = NEGOTIATE
→ requested_price = 3000
→ items = [
    {{
        "item_name": "cable",
        "quantity": 5
    }}
]
Customer: "I'll take the speaker and 3 cables."

→ items = [
    {{
        "item_name": "speaker",
        "quantity": 1
    }},
    {{
        "item_name": "cable",
        "quantity": 3
    }}
]
Intent rules:

- NEGOTIATE:
  The customer is asking for a lower price or proposing a price.

- ACCEPT:
  The customer agrees to the current offer.
  Examples:
  "okay deal"
  "deal"
  "sounds good"
  "I'll take it"
  "yes"
  "that's fine"
  "done"

- OTHER:
  The message is unrelated to negotiation or does not clearly
  indicate negotiation or acceptance.

Price rules:

- requested_price is the total amount the customer wants to pay.
- requested_discount is the discount amount requested.
- Use null when the customer does not provide a value.
- Do not invent prices or discounts.

Product rules:

- Only include products explicitly mentioned by the customer.
- Do not invent products.
- Every product MUST use the field "item_name".

Examples:

Customer: "Can you do ₹5000?"
→ intent = NEGOTIATE
→ requested_price = 5000

Customer: "Can you give me ₹500 off?"
→ intent = NEGOTIATE
→ requested_discount = 500

Customer: "No, I want ₹4800."
→ intent = NEGOTIATE
→ requested_price = 4800

Customer: "Okay deal."
→ intent = ACCEPT

Customer: "Sounds good, I'll take it."
→ intent = ACCEPT

Customer: "What is the delivery time?"
→ intent = OTHER
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