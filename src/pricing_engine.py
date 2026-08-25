def calculate_min_price(product):
    """
    Calculate the lowest price the merchant is willing
    to accept for one unit.
    """

    cost = product["cost_price"]
    min_margin_pct = product["min_margin_pct"]

    min_price = cost * (1 + min_margin_pct / 100)

    return min_price

def calculate_discount_floor(product):
    """
    Calculate the lowest allowed price considering
    both merchant margin and maximum discount.
    """

    selling_price = product["selling_price"]
    max_discount_pct = product["max_discount_pct"]

    discount_floor = selling_price * (
        1 - max_discount_pct / 100
    )

    margin_floor = calculate_min_price(product)

    return max(discount_floor, margin_floor)