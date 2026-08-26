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

def evaluate_counter_offer(product, customer_price):
    """
    Evaluate a price proposed by the customer.

    Returns:
        - ACCEPT if the customer's price is acceptable
        - COUNTER if we can negotiate further
        - REJECT if the price is below the merchant's floor
    """

    listed_price = product["selling_price"]
    floor_price = calculate_discount_floor(product)

    if customer_price < floor_price:
        return {
            "decision": "REJECT",
            "message": "Customer offer is below merchant floor.",
            "offer_price": floor_price
        }

    if customer_price >= listed_price:
        return {
            "decision": "ACCEPT",
            "message": "Customer price is at or above listed price.",
            "offer_price": customer_price
        }

    return {
        "decision": "COUNTER",
        "message": "Customer offer is acceptable but negotiation can continue.",
        "offer_price": customer_price
    }

def generate_counter_offer(product, current_offer, customer_offer):
    """
    Generate a counter-offer between the merchant's
    current offer and the customer's offer.
    """

    floor_price = calculate_discount_floor(product)

    # Customer is asking below what the merchant can accept
    if customer_offer < floor_price:
        return {
            "decision": "REJECT",
            "counter_offer": floor_price
        }

    # Customer is already offering a very good price
    if customer_offer >= current_offer:
        return {
            "decision": "ACCEPT",
            "counter_offer": customer_offer
        }

    # Move halfway toward the customer's offer
    counter_offer = (
        current_offer + customer_offer
    ) / 2

    # Never go below merchant floor
    counter_offer = max(
        counter_offer,
        floor_price
    )

    return {
        "decision": "COUNTER",
        "counter_offer": round(counter_offer, 2)
    }