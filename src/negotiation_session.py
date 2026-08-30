from src.cart_engine import (
    calculate_cart,
    calculate_cart_discount_capacity,
    generate_cart_initial_offer
)

class NegotiationSession:

    def __init__(self, cart, products):

        self.cart = cart
        self.products = products

        self.cart_summary = calculate_cart(
            cart,
            products
        )

        self.discount_info = calculate_cart_discount_capacity(
            self.cart_summary
        )

        self.original_price = (
            self.cart_summary["total_original_price"]
        )

        self.floor_price = (
            self.cart_summary["total_floor_price"]
        )

        self.current_offer = generate_cart_initial_offer(
            self.cart_summary
        )

        self.round_number = 0

        self.history = []

    def respond_to_customer_offer(self, customer_offer):

        self.round_number += 1

        # Customer is offering at or above our current offer
        if customer_offer >= self.current_offer:

            self.history.append({
                "round": self.round_number,
                "customer_offer": customer_offer,
                "agent_offer": customer_offer,
                "decision": "ACCEPT"
            })

            self.current_offer = customer_offer

            return {
                "decision": "ACCEPT",
                "offer": customer_offer
            }
        if customer_offer < self.floor_price:

            self.history.append({
                "round": self.round_number,
                "customer_offer": customer_offer,
                "agent_offer": self.current_offer,
                "decision": "BELOW_FLOOR"
            })

            return {
                "decision": "BELOW_FLOOR",
                "offer": self.current_offer
            }

                # Customer offer is above floor
        # but below our current offer.

        midpoint = (
            self.current_offer
            + customer_offer
        ) / 2

        counter_offer = max(
            midpoint,
            self.floor_price
        )

        counter_offer = round(
            counter_offer,
            2
        )

        self.current_offer = counter_offer

        self.history.append({
            "round": self.round_number,
            "customer_offer": customer_offer,
            "agent_offer": counter_offer,
            "decision": "COUNTER"
        })

        return {
            "decision": "COUNTER",
            "offer": counter_offer
        }

    def get_history(self):

        return self.history