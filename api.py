import re
import os
import hmac
import hashlib

import razorpay

from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.data_loader import load_products
from src.llm_agent import (
    extract_negotiation_request,
    NegotiationRequest,
    NegotiationItem
)
from src.cart_builder import build_cart
from src.negotiation_session import (
    NegotiationSession,
    MAX_ROUNDS
)


# ============================================================
# Environment
# ============================================================

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")


# ============================================================
# Helper Functions
# ============================================================

def extract_price_locally(message):
    """
    Extract the customer's intended price from a negotiation message.

    Handles examples such as:
        9000
        ₹9000
        Rs 9000
        I can pay 9000
        I want 2 at 9000

    When both a quantity and a price are present, the price is preferred.
    """

    text = message.lower().replace(",", "")

    # Strong price markers first.
    explicit_patterns = [
        r"(?:₹|rs\.?|inr)\s*([0-9]+(?:\.[0-9]+)?)",
        r"(?:at|for|pay|offer|do)\s*(?:₹|rs\.?|inr)?\s*([0-9]+(?:\.[0-9]+)?)"
    ]

    for pattern in explicit_patterns:
        matches = re.findall(pattern, text)

        if matches:
            try:
                return float(matches[-1])
            except ValueError:
                pass

    # Fallback: use the last number in the message.
    # This correctly handles "I want 2 at 9000".
    numbers = re.findall(
        r"[0-9]+(?:\.[0-9]+)?",
        text
    )

    if not numbers:
        return None

    try:
        return float(numbers[-1])
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
    Detect whether the customer is rejecting
    the active quantity suggestion.
    """

    text = message.lower().strip()

    rejection_phrases = [
        "only one",
        "just one",
        "one only",
        "i only need one",
        "i just need one",
        "don't need more",
        "dont need more",
        "do not need more",
        "can't buy more",
        "cant buy more",
        "cannot buy more",
        "not more",
        "no more",
        "don't want more",
        "dont want more",
        "do not want more"
    ]

    if any(
        phrase in text
        for phrase in rejection_phrases
    ):
        return True

    # Treat a leading "no" as rejection of the quantity suggestion,
    # while keeping "no problem" from being misclassified.
    if (
        (text == "no" or text.startswith("no ") or text.startswith("no,"))
        and not text.startswith("no problem")
    ):
        return True

    return text in {"nope", "nah"}


def is_purchase_rejection(message):
    """
    Detect that the customer wants to stop the purchase entirely.
    This must be checked before generic acceptance phrases such as "okay".
    """

    text = message.lower().strip()

    rejection_phrases = [
        "don't want to buy",
        "dont want to buy",
        "do not want to buy",
        "not going to buy",
        "not buying",
        "i won't buy",
        "i wont buy",
        "cancel the order",
        "cancel this",
        "cancel",
        "leave it",
        "never mind",
        "nevermind"
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
# Local Cart Parser
# ============================================================

def build_local_negotiation_request(message, products):
    """
    Try to understand simple cart messages locally.

    This avoids Gemini for normal frontend cart requests.

    Example:
        I want to buy 1 Bluetooth Speaker,
        2 USB-C Cable, 1 Laptop Stand
    """

    text = message.lower()

    items = []

    # Sort longest product names first
    # so more specific names are matched first.
    product_rows = list(products.iterrows())

    product_rows.sort(
        key=lambda x: len(
            str(x[1]["product_name"])
        ),
        reverse=True
    )

    for _, product in product_rows:

        product_name = str(
            product["product_name"]
        )

        product_lower = product_name.lower()

        if product_lower not in text:
            continue

        # Look for quantity immediately before
        # the product name.
        escaped_name = re.escape(
            product_lower
        )

        quantity_pattern = (
            r"(\d+)\s+"
            + escaped_name
        )

        quantity_match = re.search(
            quantity_pattern,
            text
        )

        if quantity_match:
            quantity = int(
                quantity_match.group(1)
            )
        else:
            quantity = 1

        items.append(
            NegotiationItem(
                item_name=product_name,
                quantity=quantity
            )
        )

    if not items:
        return None

    return NegotiationRequest(
        intent="NEGOTIATE",
        requested_price=None,
        requested_discount=None,
        items=items
    )


# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="AI Payment Negotiator",
    description="AI powered conversational price negotiation",
    version="1.0"
)


# ============================================================
# CORS
# ============================================================

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


# ============================================================
# Load Products
# ============================================================

products = load_products()


# ============================================================
# Razorpay Client
# ============================================================

razorpay_client = None

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:

    razorpay_client = razorpay.Client(
        auth=(
            RAZORPAY_KEY_ID,
            RAZORPAY_KEY_SECRET
        )
    )


# ============================================================
# Request Models
# ============================================================

class StartNegotiationRequest(BaseModel):
    message: str


class ContinueNegotiationRequest(BaseModel):
    session_id: str
    message: str


class CreatePaymentRequest(BaseModel):
    session_id: str


class VerifyPaymentRequest(BaseModel):
    session_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class DirectCheckoutItem(BaseModel):
    product_id: str
    quantity: int


class DirectCheckoutRequest(BaseModel):
    items: list[DirectCheckoutItem]


class DirectVerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ============================================================
# Temporary Session Storage
# ============================================================

sessions = {}
direct_orders = {}


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
    # 1. Try local extraction first
    # --------------------------------------------------------

    negotiation_request = (
        build_local_negotiation_request(
            request.message,
            products
        )
    )


    # --------------------------------------------------------
    # 2. If local parsing fails, use Gemini
    # --------------------------------------------------------

    if negotiation_request is None:

        try:

            negotiation_request = (
                extract_negotiation_request(
                    request.message
                )
            )

        except Exception as e:

            return {
                "success": False,
                "message": (
                    "I couldn't understand the "
                    "products in your request. "
                    f"AI service error: {str(e)}"
                )
            }


    # --------------------------------------------------------
    # 3. Build cart
    # --------------------------------------------------------

    try:

        cart = build_cart(
            negotiation_request,
            products
        )

    except Exception as e:

        return {
            "success": False,
            "message": (
                f"Unable to build cart: {str(e)}"
            )
        }


    if not cart:

        return {
            "success": False,
            "message": (
                "I couldn't identify the products "
                "in your request."
            )
        }


    # --------------------------------------------------------
    # 4. Create negotiation session
    # --------------------------------------------------------

    try:

        session = NegotiationSession(
            cart,
            products
        )

    except Exception as e:

        return {
            "success": False,
            "message": (
                f"Unable to create negotiation "
                f"session: {str(e)}"
            )
        }


    # --------------------------------------------------------
    # 5. Generate session ID
    # --------------------------------------------------------

    session_id = str(
        len(sessions) + 1
    )

    sessions[session_id] = session


    # --------------------------------------------------------
    # 6. Generate first response
    # --------------------------------------------------------

    if (
        negotiation_request.requested_price
        is not None
    ):

        result = (
            session.respond_to_customer_offer(
                negotiation_request.requested_price
            )
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

            opportunity = (
                session.quantity_opportunity
            )

            message = (
                f"If you take "
                f"{opportunity['quantity']}, "
                f"I can offer them at "
                f"₹{opportunity['unit_price']:.2f} each. "
                f"Your total would be "
                f"₹{opportunity['total_price']:.2f}, "
                f"saving you "
                f"₹{opportunity['total_saving']:.2f}. "
                f"Would you like to increase "
                f"the quantity?"
            )

        else:

            message = (
                f"I can offer this cart for "
                f"₹{session.current_offer:.2f}. "
                f"How does that sound?"
            )


    # --------------------------------------------------------
    # 7. Return response
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
                "product_name":
                    item["product_name"],

                "quantity":
                    item["quantity"],

                "unit_price":
                    item["unit_price"]
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
            "message":
                "Negotiation session not found."
        }


    message = request.message.strip()


    # ========================================================
    # 2. CUSTOMER CANCELS PURCHASE
    # ========================================================

    if is_purchase_rejection(message):

        session.quantity_opportunity = None
        session.cancelled = True

        session.history.append({
            "round": session.round_number,
            "customer_offer": None,
            "agent_offer": session.current_offer,
            "decision": "CANCELLED"
        })

        return {
            "success": True,
            "decision": "CANCELLED",
            "message": (
                "No problem. I've ended this negotiation. "
                "You can return to the cart whenever you want."
            ),
            "offer": session.current_offer,
            "round": session.round_number,
            "remaining_rounds": max(
                0,
                MAX_ROUNDS - session.round_number
            )
        }


    # ========================================================
    # 2. QUANTITY OFFER ACCEPTANCE
    # ========================================================

    if (
        session.quantity_opportunity is not None
        and is_quantity_acceptance(message)
    ):

        result = (
            session.accept_quantity_offer()
        )

        return {

            "success": True,

            "decision":
                result["decision"],

            "message": (
                f"Deal! I'll accept "
                f"{result['quantity']} units for "
                f"₹{result['offer']:.2f} total "
                f"(₹{result['offer'] / result['quantity']:.2f} each)."
            ),

            "offer":
                result["offer"],

            "quantity":
                result["quantity"],

            "cart": [

                {
                    "product_id":
                        item["product_id"],

                    "product_name":
                        item["product_name"],

                    "quantity":
                        item["quantity"],

                    "unit_price":
                        item["unit_price"]
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

            "decision":
                "PRICE_NEGOTIATION",

            "message": (
                "No problem. We can work with "
                "the quantity you need. "
                "What price did you have in mind?"
            ),

            "offer":
                session.current_offer
        }


    # ========================================================
    # 4. NORMAL DEAL ACCEPTANCE
    # ========================================================

    if is_general_acceptance(message):

        result = (
            session.accept_current_offer()
        )

        return {

            "success": True,

            "decision":
                "ACCEPT",

            "message": (
                f"Deal! I'll accept "
                f"₹{result['offer']:.2f}."
            ),

            "offer":
                result["offer"]
        }


    # ========================================================
    # 5. LOCAL PRICE EXTRACTION
    # ========================================================

    requested_price = (
        extract_price_locally(message)
    )


    # --------------------------------------------------------
    # If a clear price is present,
    # DO NOT call Gemini.
    # --------------------------------------------------------

    if requested_price is not None:

        result = (
            session.respond_to_customer_offer(
                requested_price
            )
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
                MAX_ROUNDS -
                session.round_number
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
                MAX_ROUNDS -
                session.round_number
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

            "decision":
                result["decision"],

            "message":
                response_message,

            "offer":
                result["offer"],

            "round":
                session.round_number,

            "remaining_rounds":
                max(
                    0,
                    MAX_ROUNDS -
                    session.round_number
                )
        }


    # ========================================================
    # 6. ONLY NOW USE GEMINI
    # ========================================================

    try:

        negotiation_request = (
            extract_negotiation_request(
                message
            )
        )

    except Exception as e:

        return {

            "success": False,

            "decision":
                "ERROR",

            "message": (
                "I couldn't understand that. "
                "Please enter a price such as "
                "₹4500."
            ),

            "error": str(e)
        }


    # --------------------------------------------------------
    # Gemini detected ACCEPT
    # --------------------------------------------------------

    if (
        negotiation_request.intent
        == "ACCEPT"
    ):

        result = (
            session.accept_current_offer()
        )

        return {

            "success": True,

            "decision":
                "ACCEPT",

            "message": (
                f"Deal! I'll accept "
                f"₹{result['offer']:.2f}."
            ),

            "offer":
                result["offer"]
        }


    # --------------------------------------------------------
    # Gemini detected a requested price
    # --------------------------------------------------------

    if (
        negotiation_request.requested_price
        is not None
    ):

        result = (
            session.respond_to_customer_offer(
                negotiation_request.requested_price
            )
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

            "decision":
                result["decision"],

            "message":
                response_message,

            "offer":
                result["offer"],

            "round":
                session.round_number,

            "remaining_rounds":
                max(
                    0,
                    MAX_ROUNDS -
                    session.round_number
                )
        }


    # ========================================================
    # 7. CUSTOMER DID NOT GIVE A PRICE
    # ========================================================

    return {

        "success": True,

        "decision":
            "NEED_PRICE",

        "message":
            "What price did you have in mind?",

        "offer":
            session.current_offer
    }


# ============================================================
# Direct Checkout - Buy Without Negotiation
# ============================================================

@app.post("/payment/direct/create-order")
def create_direct_payment_order(
    request: DirectCheckoutRequest
):
    if razorpay_client is None:
        return {
            "success": False,
            "message": (
                "Razorpay is not configured. "
                "Please add your Razorpay keys to .env."
            )
        }

    if not request.items:
        return {
            "success": False,
            "message": "Your cart is empty."
        }

    total_rupees = 0.0
    order_items = []

    for requested_item in request.items:

        if requested_item.quantity <= 0:
            return {
                "success": False,
                "message": "Invalid item quantity."
            }

        matches = products[
            products["product_id"]
            == requested_item.product_id
        ]

        if matches.empty:
            return {
                "success": False,
                "message": (
                    f"Product {requested_item.product_id} "
                    "was not found."
                )
            }

        product = matches.iloc[0]
        unit_price = float(
            product["selling_price"]
        )

        total_rupees += (
            unit_price
            * requested_item.quantity
        )

        order_items.append({
            "product_id":
                requested_item.product_id,
            "product_name":
                str(product["product_name"]),
            "quantity":
                requested_item.quantity,
            "unit_price":
                unit_price
        })

    amount = int(
        round(total_rupees * 100)
    )

    if amount <= 0:
        return {
            "success": False,
            "message": "Invalid payment amount."
        }

    try:
        order = razorpay_client.order.create(
            data={
                "amount": amount,
                "currency": "INR",
                "receipt":
                    f"direct_{len(direct_orders) + 1}",
                "notes": {
                    "checkout_type": "direct"
                }
            }
        )

        direct_orders[order["id"]] = {
            "status": "created",
            "amount": amount,
            "items": order_items
        }

        return {
            "success": True,
            "order_id": order["id"],
            "amount": amount,
            "currency": "INR",
            "key_id": RAZORPAY_KEY_ID
        }

    except Exception as e:
        return {
            "success": False,
            "message": (
                "Unable to create payment order: "
                f"{str(e)}"
            )
        }


@app.post("/payment/direct/verify")
def verify_direct_payment(
    request: DirectVerifyPaymentRequest
):
    if not RAZORPAY_KEY_SECRET:
        return {
            "success": False,
            "message":
                "Razorpay secret is not configured."
        }

    order_record = direct_orders.get(
        request.razorpay_order_id
    )

    if order_record is None:
        return {
            "success": False,
            "message":
                "Direct checkout order not found."
        }

    generated_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        (
            request.razorpay_order_id
            + "|"
            + request.razorpay_payment_id
        ).encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(
        generated_signature,
        request.razorpay_signature
    ):
        return {
            "success": False,
            "message":
                "Payment verification failed."
        }

    order_record["status"] = "paid"
    order_record["payment_id"] = (
        request.razorpay_payment_id
    )

    return {
        "success": True,
        "message":
            "Payment verified successfully.",
        "payment_id":
            request.razorpay_payment_id,
        "order_id":
            request.razorpay_order_id
    }


# ============================================================
# Razorpay Payment
# ============================================================

@app.post("/payment/create-order")
def create_payment_order(
    request: CreatePaymentRequest
):

    # --------------------------------------------------------
    # Check Razorpay configuration
    # --------------------------------------------------------

    if razorpay_client is None:

        return {

            "success": False,

            "message": (
                "Razorpay is not configured. "
                "Please add RAZORPAY_KEY_ID and "
                "RAZORPAY_KEY_SECRET to your .env file."
            )
        }


    # --------------------------------------------------------
    # Find session
    # --------------------------------------------------------

    session = sessions.get(
        request.session_id
    )


    if session is None:

        return {

            "success": False,

            "message":
                "Negotiation session not found."
        }


    # --------------------------------------------------------
    # Payment only after acceptance
    # --------------------------------------------------------

    if not session.accepted:

        return {

            "success": False,

            "message":
                "Please accept the negotiation deal first."
        }


    # --------------------------------------------------------
    # Amount is stored in rupees.
    # Razorpay expects paise.
    # --------------------------------------------------------

    amount = int(
        round(
            session.current_offer * 100
        )
    )


    if amount <= 0:

        return {

            "success": False,

            "message":
                "Invalid payment amount."
        }


    try:

        order = (
            razorpay_client.order.create(
                data={

                    "amount":
                        amount,

                    "currency":
                        "INR",

                    "receipt":
                        f"negotiation_{request.session_id}",

                    "notes": {

                        "session_id":
                            request.session_id,

                        "product":
                            "AI Payment Negotiator"
                    }
                }
            )
        )


        # Save Razorpay order information
        session.razorpay_order_id = (
            order["id"]
        )

        session.payment_status = (
            "created"
        )


        return {

            "success": True,

            "order_id":
                order["id"],

            "amount":
                amount,

            "currency":
                "INR",

            "key_id":
                RAZORPAY_KEY_ID
        }


    except Exception as e:

        return {

            "success": False,

            "message": (
                "Unable to create payment order: "
                f"{str(e)}"
            )
        }


# ============================================================
# Razorpay Payment Verification
# ============================================================

@app.post("/payment/verify")
def verify_payment(
    request: VerifyPaymentRequest
):

    # --------------------------------------------------------
    # Check Razorpay configuration
    # --------------------------------------------------------

    if (
        not RAZORPAY_KEY_SECRET
    ):

        return {

            "success": False,

            "message":
                "Razorpay secret is not configured."
        }


    # --------------------------------------------------------
    # Find session
    # --------------------------------------------------------

    session = sessions.get(
        request.session_id
    )


    if session is None:

        return {

            "success": False,

            "message":
                "Negotiation session not found."
        }


    try:

        # ----------------------------------------------------
        # Verify Razorpay signature
        # ----------------------------------------------------

        generated_signature = hmac.new(

            RAZORPAY_KEY_SECRET.encode(),

            (
                request.razorpay_order_id
                + "|"
                + request.razorpay_payment_id
            ).encode(),

            hashlib.sha256
        ).hexdigest()


        if not hmac.compare_digest(
            generated_signature,
            request.razorpay_signature
        ):

            return {

                "success": False,

                "message":
                    "Payment verification failed."
            }


        # ----------------------------------------------------
        # Payment verified
        # ----------------------------------------------------

        session.payment_status = "paid"

        session.razorpay_payment_id = (
            request.razorpay_payment_id
        )

        session.razorpay_order_id = (
            request.razorpay_order_id
        )


        return {

            "success": True,

            "message":
                "Payment verified successfully.",

            "payment_id":
                request.razorpay_payment_id,

            "order_id":
                request.razorpay_order_id
        }


    except Exception as e:

        return {

            "success": False,

            "message": (
                "Payment verification failed: "
                f"{str(e)}"
            )
        }




# ============================================================
# Negotiation Audit Trail
# ============================================================

@app.get("/negotiate/{session_id}/history")
def negotiation_history(session_id: str):
    """
    Return the deterministic negotiation audit trail for one session.

    Each history entry is created by NegotiationSession and records:
    - negotiation round
    - customer offer
    - agent offer
    - decision
    - quantity, when a quantity deal is accepted
    """

    session = sessions.get(session_id)

    if session is None:
        return {
            "success": False,
            "message": "Negotiation session not found."
        }

    history = session.get_history()

    return {
        "success": True,
        "session_id": session_id,
        "negotiation_mode": session.negotiation_mode,
        "round": session.round_number,
        "max_rounds": MAX_ROUNDS,
        "accepted": session.accepted,
        "original_price": round(float(session.original_price), 2),
        "floor_price": round(float(session.floor_price), 2),
        "current_offer": round(float(session.current_offer), 2),
        "history": history
    }

# ============================================================
# Merchant Dashboard
# ============================================================

@app.get("/merchant/dashboard")
def merchant_dashboard():

    # --------------------------------------------------------
    # Total negotiations
    # --------------------------------------------------------

    total_negotiations = len(
        sessions
    )


    # --------------------------------------------------------
    # Accepted negotiations
    # --------------------------------------------------------

    accepted_sessions = [

        session

        for session in sessions.values()

        if getattr(
            session,
            "accepted",
            False
        )
    ]


    # --------------------------------------------------------
    # Paid negotiations
    # --------------------------------------------------------

    paid_sessions = [

        session

        for session in accepted_sessions

        if getattr(
            session,
            "payment_status",
            ""
        ) == "paid"
    ]


    # --------------------------------------------------------
    # Revenue
    # --------------------------------------------------------

    total_revenue = sum(

        session.current_offer

        for session in paid_sessions
    )


    # --------------------------------------------------------
    # Customer savings
    # --------------------------------------------------------

    total_savings = 0

    for session in accepted_sessions:

        try:

            original = (
                session.cart_summary[
                    "total_original_price"
                ]
            )

            savings = (
                original -
                session.current_offer
            )

            total_savings += savings

        except Exception:

            pass


    # --------------------------------------------------------
    # Average discount
    # --------------------------------------------------------

    average_discount = 0

    if accepted_sessions:

        discounts = []


        for session in accepted_sessions:

            try:

                original = (
                    session.cart_summary[
                        "total_original_price"
                    ]
                )


                if original > 0:

                    discount = (

                        (
                            original -
                            session.current_offer
                        )
                        /
                        original

                    ) * 100


                    discounts.append(
                        discount
                    )

            except Exception:

                continue


        if discounts:

            average_discount = (
                sum(discounts)
                /
                len(discounts)
            )


    # --------------------------------------------------------
    # Return dashboard data
    # --------------------------------------------------------

    return {

        "success": True,

        "total_negotiations":
            total_negotiations,

        "accepted_deals":
            len(accepted_sessions),

        "paid_orders":
            len(paid_sessions),

        "revenue":
            round(
                total_revenue,
                2
            ),

        "customer_savings":
            round(
                total_savings,
                2
            ),

        "average_discount":
            round(
                average_discount,
                2
            )
    }