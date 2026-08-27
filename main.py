from src.data_loader import load_products

from src.cart_engine import (
    calculate_cart,
    allocate_discount
)


products = load_products()


cart = [
    {
        "product_id": "P010",
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


requested_discount = 500


allocations = allocate_discount(
    cart_summary,
    requested_discount
)


print("\n===== CART =====")

for item in cart_summary["cart_details"]:

    print(
        f"{item['product_name']} × "
        f"{item['quantity']} | "
        f"₹{item['original_value']:.0f}"
    )


print("\n===== DISCOUNT ALLOCATION =====")

total_allocated = 0

for item in allocations:

    print(
        f"{item['product_name']} | "
        f"Negotiability: "
        f"{item['negotiability_score']}/100 | "
        f"Discount: "
        f"₹{item['allocated_discount']:.2f}"
    )

    total_allocated += item[
        "allocated_discount"
    ]


print("\n===== RESULT =====")

print(
    f"Customer requested: ₹{requested_discount:.2f}"
)

print(
    f"Actually allocated: ₹{total_allocated:.2f}"
)