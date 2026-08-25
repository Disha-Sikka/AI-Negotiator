from pricing_engine import calculate_discount_floor


def initial_offer(product, negotiation_strength=0.25):
    """
    Create the first offer.

    negotiation_strength:
        0 = almost no discount
        1 = immediately offer the lowest allowed price
    """

    listed_price = product["selling_price"]
    floor_price = calculate_discount_floor(product)

    discount_range = listed_price - floor_price

    offer = listed_price - (
        discount_range * negotiation_strength
    )

    return round(offer, 2)