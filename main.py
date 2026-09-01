from src.data_loader import load_products
from src.llm_agent import extract_negotiation_request
from src.product_resolver import resolve_product
from src.cart_builder import build_cart
from src.negotiation_session import NegotiationSession


# ==========================================
# LOAD PRODUCT CATALOG
# ==========================================

products = load_products()


print("\n===== AI PAYMENT NEGOTIATOR =====")


# ==========================================
# STEP 1: GET INITIAL CUSTOMER MESSAGE
# ==========================================

customer_message = input("\nYou: ")


# ==========================================
# STEP 2: UNDERSTAND CUSTOMER MESSAGE
# ==========================================

request = extract_negotiation_request(
    customer_message
)


print("\n===== GEMINI REQUEST =====")
print(request)


# ==========================================
# STEP 3: RESOLVE PRODUCTS
# ==========================================

print("\n===== PRODUCT RESOLUTION =====")

for item in request.items:

    product = resolve_product(
        item.item_name,
        products
    )

    if product:

        print(
            f"{item.item_name} "
            f"→ "
            f"{product['product_name']} "
            f"({product['product_id']})"
        )

    else:

        print(
            f"{item.item_name} → NOT FOUND"
        )


# ==========================================
# STEP 4: BUILD CART
# ==========================================

cart = build_cart(
    request,
    products
)


print("\n===== GENERATED CART =====")

for item in cart:

    print(
        f"{item['product_name']} × "
        f"{item['quantity']} | "
        f"₹{item['unit_price']:.2f}"
    )


# ==========================================
# STEP 5: CREATE NEGOTIATION SESSION
# ==========================================

session = NegotiationSession(
    cart,
    products
)


print("\n===== NEGOTIATION SESSION =====")

print(
    f"Mode: {session.negotiation_mode}"
)

print(
    f"Original cart: "
    f"₹{session.original_price:.2f}"
)

print(
    f"Merchant floor: "
    f"₹{session.floor_price:.2f}"
)

print(
    f"Initial AI offer: "
    f"₹{session.current_offer:.2f}"
)


# ==========================================
# STEP 6: PROCESS INITIAL OFFER
# ==========================================

if request.requested_price is not None:

    result = session.respond_to_customer_offer(
        request.requested_price
    )

    print("\n===== NEGOTIATION =====")

    if result["decision"] == "ACCEPT":

        print(
            f"AI: Deal! "
            f"I can accept ₹{result['offer']:.2f}."
        )

    elif result["decision"] == "COUNTER":

        print(
            f"AI: I can't go as low as "
            f"₹{request.requested_price:.2f}, "
            f"but I can offer "
            f"₹{result['offer']:.2f}."
        )

    elif result["decision"] == "BELOW_FLOOR":

        print(
            f"AI: That's below the lowest price "
            f"I can offer. I can do "
            f"₹{result['offer']:.2f}."
        )


# ==========================================
# STEP 7: CONTINUE NEGOTIATION
# ==========================================

while True:

    customer_message = input("\nYou: ")

    if customer_message.lower() in [
        "exit",
        "quit",
        "done"
    ]:

        print("\nNegotiation ended.")
        break


    # Ask Gemini to understand the new message

    request = extract_negotiation_request(
        customer_message
    )


    print("\n===== GEMINI REQUEST =====")
    print(request)


    # --------------------------------------
    # Customer accepts current offer
    # --------------------------------------

    if request.intent == "ACCEPT":

        print(
            f"\nAI: Deal! "
            f"I'll accept ₹{session.current_offer:.2f}."
        )

        break


    # --------------------------------------
    # Customer provided a price
    # --------------------------------------

    elif request.requested_price is not None:

        result = session.respond_to_customer_offer(
            request.requested_price
        )

        if result["decision"] == "ACCEPT":

            print(
                f"\nAI: Deal! "
                f"I'll accept ₹{result['offer']:.2f}."
            )

            break


        elif result["decision"] == "COUNTER":

            print(
                f"\nAI: I can improve the price to "
                f"₹{result['offer']:.2f}."
            )


        elif result["decision"] == "BELOW_FLOOR":

            print(
                f"\nAI: I can't go that low. "
                f"My best available price is "
                f"₹{result['offer']:.2f}."
            )


    # --------------------------------------
    # Customer didn't provide a price
    # --------------------------------------

    else:

        print(
            "\nAI: What price did you have in mind?"
        )