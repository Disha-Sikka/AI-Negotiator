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