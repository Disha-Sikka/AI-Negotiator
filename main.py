from src.data_loader import load_products
from src.llm_agent import extract_negotiation_request
from src.product_resolver import resolve_product
from src.cart_builder import build_cart


products = load_products()


customer_message = (
    "I'll take the speaker, cable and laptop stand. "
    "Can you give me a good deal?"
)


request = extract_negotiation_request(
    customer_message
)


print("\n===== GEMINI REQUEST =====")
print(request)


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