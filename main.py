from src.data_loader import load_products
from src.llm_agent import extract_negotiation_request
from src.product_resolver import resolve_product
from src.cart_builder import build_cart
from src.negotiation_session import NegotiationSession


# Load product catalog
products = load_products()


# Customer's message
customer_message = (
    "I'll take the speaker, cable and laptop stand. "
    "Can you do ₹5000?"
)


# 1. Understand customer message
request = extract_negotiation_request(
    customer_message
)

print("\n===== GEMINI REQUEST =====")
print(request)


# 2. Resolve products
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


# 3. Build cart
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


# 4. Start negotiation session
session = NegotiationSession(
    cart,
    products
)


print("\n===== NEGOTIATION SESSION =====")

print(
    f"Negotiation mode: "
    f"{session.negotiation_mode}"
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

# 5. Process customer's price offer

if request.requested_price is not None:

    result = session.respond_to_customer_offer(
        request.requested_price
    )

    print("\n===== NEGOTIATION RESULT =====")

    print(
        f"Customer offered: "
        f"₹{request.requested_price:.2f}"
    )

    print(
        f"Decision: "
        f"{result['decision']}"
    )

    print(
        f"Agent offer: "
        f"₹{result['offer']:.2f}"
    )