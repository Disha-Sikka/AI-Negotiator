from src.data_loader import load_products

from src.cart_engine import (
    calculate_cart,
    calculate_cart_discount_capacity,
    generate_cart_initial_offer
)


products = load_products()


cart = [
    {
        "product_id": "P002",
        "quantity": 1
    },
    {
        "product_id": "P003",
        "quantity": 2
    },
    {
        "product_id": "P007",
        "quantity": 1
    }
]


cart_summary = calculate_cart(
    cart,
    products
)


discount_info = calculate_cart_discount_capacity(
    cart_summary
)


initial_offer = generate_cart_initial_offer(
    cart_summary
)


print("\n===== CART =====")

for item in cart_summary["cart_details"]:

    print(
        f"{item['product_name']} × "
        f"{item['quantity']} | "
        f"₹{item['original_value']:.0f}"
    )


print("\n===== SUMMARY =====")

print(
    f"Original cart: "
    f"₹{cart_summary['total_original_price']:.2f}"
)

print(
    f"Merchant floor: "
    f"₹{cart_summary['total_floor_price']:.2f}"
)

print(
    f"Maximum discount: "
    f"₹{discount_info['discount_capacity']:.2f}"
)

print(
    f"Maximum discount %: "
    f"{discount_info['discount_percentage']:.2f}%"
)

print(
    f"Initial AI offer: "
    f"₹{initial_offer:.2f}"
)