def inventory_age_score(age_days):
    """
    Older inventory gets a higher negotiation score.
    """

    if age_days >= 120:
        return 100

    if age_days >= 90:
        return 80

    if age_days >= 60:
        return 60

    if age_days >= 30:
        return 40

    return 20

def demand_score(demand_level):
    """
    Lower demand means the product is more negotiable.
    """

    if demand_level == "low":
        return 100

    if demand_level == "medium":
        return 60

    if demand_level == "high":
        return 20

    return 50

def inventory_score(inventory):
    """
    Higher inventory means more willingness to negotiate.
    """

    if inventory >= 500:
        return 100

    if inventory >= 250:
        return 80

    if inventory >= 100:
        return 60

    if inventory >= 50:
        return 40

    return 20

def margin_score(product):
    """
    Higher margin means more room for negotiation.
    """

    selling_price = product["selling_price"]
    cost_price = product["cost_price"]

    margin = (
        (selling_price - cost_price)
        / selling_price
    ) * 100

    if margin >= 50:
        return 100

    if margin >= 40:
        return 80

    if margin >= 30:
        return 60

    if margin >= 20:
        return 40

    return 20

def calculate_negotiability_score(product):
    """
    Calculate an overall negotiability score from 0–100.
    """

    age = inventory_age_score(
        product["inventory_age_days"]
    )

    demand = demand_score(
        product["demand_level"]
    )

    inventory = inventory_score(
        product["inventory"]
    )

    margin = margin_score(product)

    score = (
        age * 0.30
        + demand * 0.25
        + inventory * 0.20
        + margin * 0.25
    )

    return round(score, 2)

def calculate_item_negotiability(product, quantity):
    """
    Calculate negotiability for a specific cart item.

    Product-level factors:
    - inventory age
    - demand
    - inventory
    - margin

    Transaction-level factor:
    - quantity
    """

    product_score = calculate_negotiability_score(product)

    qty_score = quantity_score(quantity)

    # 80% product economics
    # 20% quantity signal
    final_score = (
        product_score * 0.80
        + qty_score * 0.20
    )

    return round(final_score, 2)

def quantity_score(quantity):
    """
    Higher quantity means stronger justification
    for a quantity-based discount.
    """

    if quantity >= 10:
        return 100

    if quantity >= 5:
        return 80

    if quantity >= 3:
        return 60

    if quantity == 2:
        return 40

    return 0

def cart_size_score(cart):
    """
    Score the size of a customer's cart.

    More distinct products indicate stronger
    cart-level negotiation potential.
    """

    distinct_products = len(cart)

    if distinct_products >= 5:
        return 100

    if distinct_products >= 4:
        return 80

    if distinct_products >= 3:
        return 60

    if distinct_products == 2:
        return 30

    return 0