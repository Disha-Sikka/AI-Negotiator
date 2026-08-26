import pandas as pd

from src.pricing_engine import calculate_discount_floor

def calculate_cart(cart, products):
    """
    Calculate the original value and minimum acceptable
    value of a customer's cart.
    """

    total_original_price = 0
    total_floor_price = 0

    cart_details = []

    for item in cart:

        product_id = item["product_id"]
        quantity = item["quantity"]

        product = products[
            products["product_id"] == product_id
        ]

        if product.empty:
            raise ValueError(
                f"Product {product_id} not found."
            )

        product = product.iloc[0]

        selling_price = product["selling_price"]

        floor_price = calculate_discount_floor(product)

        original_value = selling_price * quantity
        floor_value = floor_price * quantity

        total_original_price += original_value
        total_floor_price += floor_value

        cart_details.append({
            "product_id": product_id,
            "product_name": product["product_name"],
            "quantity": quantity,
            "selling_price": selling_price,
            "floor_price": floor_price,
            "original_value": original_value,
            "floor_value": floor_value
        })

    return {
        "cart_details": cart_details,
        "total_original_price": total_original_price,
        "total_floor_price": total_floor_price
    }

def calculate_cart_discount_capacity(cart_summary):
    """
    Calculate how much discount is available
    between the original cart price and the
    merchant's minimum acceptable cart price.
    """

    original_price = cart_summary["total_original_price"]
    floor_price = cart_summary["total_floor_price"]

    discount_capacity = original_price - floor_price

    discount_percentage = (
        discount_capacity / original_price
    ) * 100

    return {
        "discount_capacity": round(
            discount_capacity, 2
        ),
        "discount_percentage": round(
            discount_percentage, 2
        )
    }

def generate_cart_initial_offer(
    cart_summary,
    negotiation_strength=0.25
):
    """
    Generate the first offer for a mixed cart.

    negotiation_strength:
        0 = no discount
        1 = maximum allowable discount
    """

    original_price = cart_summary[
        "total_original_price"
    ]

    floor_price = cart_summary[
        "total_floor_price"
    ]

    discount_capacity = (
        original_price - floor_price
    )

    discount = (
        discount_capacity
        * negotiation_strength
    )

    offer_price = original_price - discount

    return round(offer_price, 2)