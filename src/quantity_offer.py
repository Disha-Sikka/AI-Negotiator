from src.pricing_engine import calculate_discount_floor


def calculate_quantity_offer(product, quantity):
    """
    Calculate a quantity-based offer for a product.

    The offer must:
    1. Be lower than the regular selling price.
    2. Stay above the merchant's floor price.
    3. Give a better per-unit price for larger quantities.
    """

    selling_price = float(product["selling_price"])
    floor_price = float(calculate_discount_floor(product))

    # Quantity discount based on number of units
    if quantity >= 10:
        discount_pct = 0.12
    elif quantity >= 5:
        discount_pct = 0.10
    elif quantity >= 3:
        discount_pct = 0.07
    elif quantity == 2:
        discount_pct = 0.05
    else:
        return None

    discounted_unit_price = selling_price * (
        1 - discount_pct
    )

    # Never go below merchant floor
    unit_price = max(
        discounted_unit_price,
        floor_price
    )

    total_price = unit_price * quantity

    normal_total = selling_price * quantity

    total_saving = normal_total - total_price

    return {
        "quantity": quantity,
        "unit_price": round(unit_price, 2),
        "total_price": round(total_price, 2),
        "normal_total": round(normal_total, 2),
        "total_saving": round(total_saving, 2),
        "discount_percentage": round(
            (total_saving / normal_total) * 100,
            2
        )
    }


def find_quantity_opportunity(
    product,
    current_quantity
):
    """
    Find the best quantity offer above the customer's
    current quantity.
    """

    if current_quantity >= 10:
        return None

    # Suggest the next meaningful quantity tier
    if current_quantity == 1:
        suggested_quantity = 2

    elif current_quantity == 2:
        suggested_quantity = 3

    elif current_quantity < 5:
        suggested_quantity = 5

    else:
        suggested_quantity = 10

    return calculate_quantity_offer(
        product,
        suggested_quantity
    )