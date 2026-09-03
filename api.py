import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.data_loader import load_products
from src.llm_agent import extract_negotiation_request
from src.cart_builder import build_cart
from src.negotiation_session import (
    NegotiationSession,
    MAX_ROUNDS
)


# ============================================================
# Helper Functions
# ============================================================

def extract_price_locally(message):
    """
    Extract a price directly from simple customer messages.

    Examples:
        4500
        ₹4500
        Rs 4500
        I can do 4,500
        I can pay ₹4,500
    """

    pattern = r"(?:₹|rs\.?|inr)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)"

    match = re.search(
        pattern,
        message.lower()
    )

    if not match:
        return None

    value = match.group(1).replace(",", "")

    try:
        return float(value)
    except ValueError:
        return None


def is_quantity_acceptance(message):
    """
    Detect whether the customer is accepting
    the active quantity suggestion.
    """

    text = message.lower().strip()

    acceptance_phrases = [
        "yes",
        "yeah",
        "yep",
        "sure",
        "okay",
        "ok",
        "deal",
        "sounds good",
        "i'll take",
        "i will take",
        "i can buy",
        "buy 2",
        "take 2",
        "let's do 2",
        "lets do 2"
    ]

    return any(
        phrase in text
        for phrase in acceptance_phrases
    )


def is_quantity_rejection(message):
    """
    Detect whether the customer does not want
    to increase quantity.
    """

    text = message.lower().strip()

    rejection_phrases = [
        "only one",
        "just one",
        "one only",
        "i only need one",
        "i just need one",
        "don't need more",
        "do not need more",
        "can't buy more",
        "cannot buy more",
        "not more",
        "no more",
        "don't want more",
        "do not want more"
    ]

    return any(
        phrase in text
        for phrase in rejection_phrases
    )


def is_general_acceptance(message):
    """
    Detect a normal deal acceptance.
    """

    text = message.lower().strip()

    acceptance_phrases = [
        "deal",
        "okay deal",
        "ok deal",
        "yes",
        "yes deal",
        "accept",
        "accepted",
        "sounds good",
        "that's fine",
        "that works",
        "i'll take it",
        "i will take it"
    ]

    return any(
        phrase in text
        for phrase in acceptance_phrases
    )


# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="AI Payment Negotiator",
    description="AI powered conversational price negotiation",
    version="1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Load products once
products = load_products()


# ============================================================
# Request Models
# ============================================================

class StartNegotiationRequest(BaseModel):
    message: str


class ContinueNegotiationRequest(BaseModel):
    session_id: str
    message: str


# ============================================================
# Temporary Session Storage
# ============================================================

sessions = {}


# ============================================================
# Health Check
# ============================================================

@app.get("/")
def home():

    return {
        "status": "online",
        "service": "AI Payment Negotiator"
    }


# ============================================================
# Start Negotiation
# ============================================================

@app.post("/negotiate/start")
def start_negotiation(
    request: StartNegotiationRequest
):

    # --------------------------------------------------------
    # 1. Extract customer's request using Gemini
    # --------------------------------------------------------

    negotiation_request = extract_negotiation_request(
        request.message
    )


    # --------------------------------------------------------
    # 2. Build cart
    # --------------------------------------------------------

    cart = build_cart(
        negotiation_request,
        products
    )


    if not cart:

        return {
            "success": False,
            "message": (
                "I couldn't identify the products "
                "in your request."
            )
        }


    # --------------------------------------------------------
    # 3. Create negotiation session
    # --------------------------------------------------------

    session = NegotiationSession(
        cart,
        products
    )


    # --------------------------------------------------------
    # 4. Generate session ID
    # --------------------------------------------------------

    session_id = str(len(sessions) + 1)

    sessions[session_id] = session


    # --------------------------------------------------------
    # 5. Generate first response
    # --------------------------------------------------------

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

        elif result["decision"] == "FINAL_OFFER":

            message = (
                f"This is the best price I can offer: "
                f"₹{result['offer']:.2f}. "
                f"This is my final offer."
            )

        else:

            message = (
                f"That's below the lowest price "
                f"I can offer. I can do "
                f"₹{result['offer']:.2f}."
            )


    else:

        # ----------------------------------------------------
        # Quantity-first strategy
        # ----------------------------------------------------

        if session.quantity_opportunity is not None:

            opportunity = session.quantity_opportunity

            message = (
                f"If you take {opportunity['quantity']}, "
                f"I can offer them at "
                f"₹{opportunity['unit_price']:.2f} each. "
                f"Your total would be "
                f"₹{opportunity['total_price']:.2f}, "
                f"saving you "
                f"₹{opportunity['total_saving']:.2f}. "
                f"Would you like to increase the quantity?"
            )

        else:

            message = (
                f"I can offer this cart for "
                f"₹{session.current_offer:.2f}. "
                f"How does that sound?"
            )


    # --------------------------------------------------------
    # 6. Return response
    # --------------------------------------------------------

    return {

        "success": True,

        "session_id": session_id,

        "message": message,

        "offer": session.current_offer,

        "quantity_opportunity":
            session.quantity_opportunity,

        "cart": [
            {
                "product_name": item["product_name"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"]
            }
            for item in cart
        ]
    }


# ============================================================
# Continue Negotiation
# ============================================================

@app.post("/negotiate/continue")
def continue_negotiation(
    request: ContinueNegotiationRequest
):

    # --------------------------------------------------------
    # 1. Find session
    # --------------------------------------------------------

    session = sessions.get(
        request.session_id
    )


    if session is None:

        return {
            "success": False,
            "message": "Negotiation session not found."
        }


    message = request.message.strip()


    # ========================================================
    # 2. QUANTITY OFFER ACCEPTANCE
    # ========================================================

    if (
        session.quantity_opportunity is not None
        and is_quantity_acceptance(message)
    ):

        result = session.accept_quantity_offer()

        return {

            "success": True,

            "decision": result["decision"],

            "message": (
                f"Deal! I'll accept "
                f"{result['quantity']} units for "
                f"₹{result['offer']:.2f} total "
                f"(₹{result['offer'] / result['quantity']:.2f} each)."
            ),

            "offer": result["offer"],

            "quantity": result["quantity"],

            "cart": [
                {
                    "product_id": item["product_id"],
                    "product_name": item["product_name"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"]
                }
                for item in session.cart
            ]
        }


    # ========================================================
    # 3. QUANTITY OFFER REJECTION
    # ========================================================

    if (
        session.quantity_opportunity is not None
        and is_quantity_rejection(message)
    ):

        session.quantity_opportunity = None

        return {

            "success": True,

            "decision": "PRICE_NEGOTIATION",

            "message": (
                "No problem. We can work with "
                "the quantity you need. "
                "What price did you have in mind?"
            ),

            "offer": session.current_offer
        }


    # ========================================================
    # 4. NORMAL DEAL ACCEPTANCE
    # ========================================================

    if is_general_acceptance(message):

        result = session.accept_current_offer()

        return {

            "success": True,

            "decision": "ACCEPT",

            "message": (
                f"Deal! I'll accept "
                f"₹{result['offer']:.2f}."
            ),

            "offer": result["offer"]
        }


    # ========================================================
    # 5. LOCAL PRICE EXTRACTION
    # ========================================================

    requested_price = extract_price_locally(
        message
    )


    # If a clear price is present,
    # DO NOT call Gemini.
    if requested_price is not None:

        result = session.respond_to_customer_offer(
            requested_price
        )


        # ----------------------------------------------------
        # ACCEPT
        # ----------------------------------------------------

        if result["decision"] == "ACCEPT":

            response_message = (
                f"Deal! I'll accept "
                f"₹{result['offer']:.2f}."
            )


        # ----------------------------------------------------
        # COUNTER
        # ----------------------------------------------------

        elif result["decision"] == "COUNTER":

            remaining = (
                MAX_ROUNDS - session.round_number
            )

            response_message = (
                f"I can improve the price to "
                f"₹{result['offer']:.2f}."
            )

            if remaining > 0:

                response_message += (
                    f" You have {remaining} "
                    f"negotiation attempts remaining."
                )


        # ----------------------------------------------------
        # BELOW FLOOR
        # ----------------------------------------------------

        elif result["decision"] == "BELOW_FLOOR":

            remaining = (
                MAX_ROUNDS - session.round_number
            )

            response_message = (
                f"I can't go that low. "
                f"My best available price is "
                f"₹{result['offer']:.2f}."
            )

            if remaining > 0:

                response_message += (
                    f" You have {remaining} "
                    f"negotiation attempts remaining."
                )


        # ----------------------------------------------------
        # FINAL OFFER
        # ----------------------------------------------------

        else:

            response_message = (
                f"I've reached my final offer of "
                f"₹{result['offer']:.2f}. "
                f"I can't make any further changes."
            )


        return {

            "success": True,

            "decision": result["decision"],

            "message": response_message,

            "offer": result["offer"],

            "round": session.round_number,

            "remaining_rounds": max(
                0,
                MAX_ROUNDS - session.round_number
            )
        }


    # ========================================================
    # 6. ONLY NOW USE GEMINI
    # ========================================================

    negotiation_request = (
        extract_negotiation_request(message)
    )


    # --------------------------------------------------------
    # Gemini detected ACCEPT
    # --------------------------------------------------------

    if negotiation_request.intent == "ACCEPT":

        result = session.accept_current_offer()

        return {

            "success": True,

            "decision": "ACCEPT",

            "message": (
                f"Deal! I'll accept "
                f"₹{result['offer']:.2f}."
            ),

            "offer": result["offer"]
        }


    # --------------------------------------------------------
    # Gemini detected a requested price
    # --------------------------------------------------------

    if negotiation_request.requested_price is not None:

        result = session.respond_to_customer_offer(
            negotiation_request.requested_price
        )


        if result["decision"] == "ACCEPT":

            response_message = (
                f"Deal! I'll accept "
                f"₹{result['offer']:.2f}."
            )


        elif result["decision"] == "COUNTER":

            response_message = (
                f"I can improve the price to "
                f"₹{result['offer']:.2f}."
            )


        elif result["decision"] == "BELOW_FLOOR":

            response_message = (
                f"I can't go that low. "
                f"My best available price is "
                f"₹{result['offer']:.2f}."
            )


        else:

            response_message = (
                f"I've reached my final offer of "
                f"₹{result['offer']:.2f}. "
                f"I can't make any further changes."
            )


        return {

            "success": True,

            "decision": result["decision"],

            "message": response_message,

            "offer": result["offer"],

            "round": session.round_number,

            "remaining_rounds": max(
                0,
                MAX_ROUNDS - session.round_number
            )
        }


    # ========================================================
    # 7. CUSTOMER DID NOT GIVE A PRICE
    # ========================================================

    return {

        "success": True,

        "decision": "NEED_PRICE",

        "message": (
            "What price did you have in mind?"
        ),

        "offer": session.current_offer
    }