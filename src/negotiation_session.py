from src.cart_engine import (
    calculate_cart,
    calculate_cart_discount_capacity,
    generate_cart_initial_offer,
    allocate_discount
)

from src.negotiability import calculate_item_negotiability


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

        # Calculate item-level negotiability
        self.item_negotiability = []

        for item in self.cart_summary["cart_details"]:

            score = calculate_item_negotiability(
                item["product"],
                item["quantity"]
            )

            item["negotiability_score"] = score

            self.item_negotiability.append({
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "quantity": item["quantity"],
                "score": score
            })

        # Calculate overall cart negotiability
        self.negotiability_score = (
            self.calculate_cart_negotiability()
        )

        # Convert negotiability into initial
        # negotiation strength.
        #
        # Score 0   -> 20%
        # Score 100 -> 40%

        self.negotiation_strength = (
            0.20
            + (self.negotiability_score / 100) * 0.20
        )

        self.current_offer = generate_cart_initial_offer(
            self.cart_summary,
            negotiation_strength=self.negotiation_strength
        )

        self.round_number = 0
        self.history = []

        self.negotiation_mode = (
            self.determine_negotiation_mode()
        )

    def calculate_cart_negotiability(self):

        total_value = 0
        weighted_score = 0

        for item in self.cart_summary["cart_details"]:

            score = item["negotiability_score"]

            value = item["original_value"]

            total_value += value

            weighted_score += (
                score * value
            )

        if total_value == 0:
            return 0

        return round(
            weighted_score / total_value,
            2
        )

    def generate_item_discount_allocation(
        self,
        requested_discount
    ):

        return allocate_discount(
            self.cart_summary,
            requested_discount
        )

    def respond_to_customer_offer(
        self,
        customer_offer
    ):

        self.round_number += 1

        # Customer is below merchant floor
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

        # Customer meets current offer
        # OR reaches merchant floor
        if (
            customer_offer >= self.current_offer
            or customer_offer == self.floor_price
        ):

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

        # Customer offer is between
        # floor and current offer

        concession_rates = {
            1: 0.20,
            2: 0.25,
            3: 0.30,
            4: 0.35,
            5: 0.40
        }

        base_rate = concession_rates.get(
            self.round_number,
            0.40
        )

        # More negotiable carts receive
        # slightly larger concessions.

        negotiability_bonus = (
            self.negotiability_score / 100
        ) * 0.10

        concession_rate = (
            base_rate
            + negotiability_bonus
        )

        # Never concede more than 50%
        # of the current gap.

        concession_rate = min(
            concession_rate,
            0.50
        )

        gap = (
            self.current_offer
            - customer_offer
        )

        concession = (
            gap * concession_rate
        )

        counter_offer = (
            self.current_offer
            - concession
        )

        # HARD MERCHANT FLOOR

        counter_offer = max(
            counter_offer,
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

    def determine_negotiation_mode(self):

        distinct_products = len(self.cart)

        total_units = sum(
            item["quantity"]
            for item in self.cart
        )

        if distinct_products == 1:

            if total_units == 1:
                return "SINGLE_ITEM"

            return "QUANTITY"

        return "CART"