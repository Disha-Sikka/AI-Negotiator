from fastapi import FastAPI
from pydantic import BaseModel

from src.data_loader import load_products
from src.llm_agent import extract_negotiation_request
from src.cart_builder import build_cart
from src.negotiation_session import NegotiationSession


app = FastAPI(
    title="AI Payment Negotiator",
    description="AI powered conversational price negotiation",
    version="1.0"
)


products = load_products()


# -----------------------------
# Request Models
# -----------------------------

class StartNegotiationRequest(BaseModel):
    message: str


class ContinueNegotiationRequest(BaseModel):
    session_id: str
    message: str


# -----------------------------
# Temporary session storage
# -----------------------------

sessions = {}


# -----------------------------
# Health Check
# -----------------------------

@app.get("/")
def home():

    return {
        "status": "online",
        "service": "AI Payment Negotiator"
    }


# -----------------------------
# Start Negotiation
# -----------------------------

@app.post("/negotiate/start")
def start_negotiation(
    request: StartNegotiationRequest
):

    # Extract customer's request
    negotiation_request = (
        extract_negotiation_request(
            request.message
        )
    )

    # Build cart
    cart = build_cart(
        negotiation_request,
        products
    )

    if not cart:

        return {
            "success": False,
            "message": "I couldn't identify the products in your request."
        }

    # Create negotiation session
    session = NegotiationSession(
        cart,
        products
    )

    # Generate session ID
    session_id = str(len(sessions) + 1)

    sessions[session_id] = session

    # Customer facing response
    if negotiation_request.requested_price is not None:

        result = session.respond_to_customer_offer(
            negotiation_request.requested_price
        )

        if result["decision"] == "ACCEPT":

            message = (
                f"Deal! I can accept "
                f"₹{result['offer']:.2f}."
            )

        elif result["decision"] == "COUNTER":

            message = (
                f"I can't go as low as "
                f"₹{negotiation_request.requested_price:.2f}, "
                f"but I can offer "
                f"₹{result['offer']:.2f}."
            )

        else:

            message = (
                f"That's below the lowest price "
                f"I can offer. I can do "
                f"₹{result['offer']:.2f}."
            )

    else:

        message = (
            f"I can offer this cart for "
            f"₹{session.current_offer:.2f}. "
            f"How does that sound?"
        )

    return {
        "success": True,
        "session_id": session_id,
        "message": message,
        "offer": session.current_offer,
        "cart": [
            {
                "product_name": item["product_name"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"]
            }
            for item in cart
        ]
    }


# -----------------------------
# Continue Negotiation
# -----------------------------

@app.post("/negotiate/continue")
def continue_negotiation(
    request: ContinueNegotiationRequest
):

    session = sessions.get(
        request.session_id
    )

    if session is None:

        return {
            "success": False,
            "message": "Negotiation session not found."
        }

    # Extract customer message
    negotiation_request = (
        extract_negotiation_request(
            request.message
        )
    )

    # Customer accepted
    if negotiation_request.intent == "ACCEPT":

        return {
            "success": True,
            "decision": "ACCEPT",
            "message": (
                f"Deal! I'll accept "
                f"₹{session.current_offer:.2f}."
            ),
            "offer": session.current_offer
        }

    # Customer provided price
    if negotiation_request.requested_price is not None:

        result = session.respond_to_customer_offer(
            negotiation_request.requested_price
        )

        if result["decision"] == "ACCEPT":

            message = (
                f"Deal! I'll accept "
                f"₹{result['offer']:.2f}."
            )

        elif result["decision"] == "COUNTER":

            message = (
                f"I can improve the price to "
                f"₹{result['offer']:.2f}."
            )

        else:

            message = (
                f"I can't go that low. "
                f"My best available price is "
                f"₹{result['offer']:.2f}."
            )

        return {
            "success": True,
            "decision": result["decision"],
            "message": message,
            "offer": result["offer"]
        }

    return {
        "success": True,
        "decision": "NEED_PRICE",
        "message": (
            "What price did you have in mind?"
        ),
        "offer": session.current_offer
    }