from src.cart_engine import (
    calculate_cart,
    calculate_cart_discount_capacity,
    generate_cart_initial_offer,
    allocate_discount
)

from src.negotiability import calculate_item_negotiability
from src.quantity_offer import find_quantity_opportunity


MAX_ROUNDS = 5


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

        # Item-level negotiability
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

        # Overall cart negotiability
        self.negotiability_score = (
            self.calculate_cart_negotiability()
        )

        # Score 0 -> 20%
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
        self.accepted = False

        # Quantity upsell opportunity
        self.quantity_opportunity = (
            self.find_quantity_opportunity()
        )

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

    def find_quantity_opportunity(self):

        # Only suggest quantity increase for a
        # single-product cart for now.
        if len(self.cart_summary["cart_details"]) != 1:
            return None

        item = self.cart_summary["cart_details"][0]

        product = item["product"]
        current_quantity = item["quantity"]

        return find_quantity_opportunity(
            product,
            current_quantity
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
        if self.round_number >= MAX_ROUNDS:
            return {
                "decision": "FINAL_OFFER",
                "offer": self.current_offer
            }
        # Every customer price attempt counts as one round
        self.round_number += 1

        # Customer accepts the current AI offer
        if customer_offer >= self.current_offer:

            self.current_offer = customer_offer
            self.accepted = True

            self.history.append({
                "round": self.round_number,
                "customer_offer": customer_offer,
                "agent_offer": customer_offer,
                "decision": "ACCEPT"
            })

            return {
                "decision": "ACCEPT",
                "offer": customer_offer
            }

        # Customer is below merchant floor
        if customer_offer < self.floor_price:

            # If this was the 5th attempt,
            # stop negotiation.
            if self.round_number >= MAX_ROUNDS:

                self.history.append({
                    "round": self.round_number,
                    "customer_offer": customer_offer,
                    "agent_offer": self.current_offer,
                    "decision": "FINAL_OFFER"
                })

                return {
                    "decision": "FINAL_OFFER",
                    "offer": self.current_offer
                }

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

        # Concession rates
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

        negotiability_bonus = (
            self.negotiability_score / 100
        ) * 0.10

        concession_rate = (
            base_rate
            + negotiability_bonus
        )

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

        # Fifth attempt = final offer
        if self.round_number >= MAX_ROUNDS:

            self.history.append({
                "round": self.round_number,
                "customer_offer": customer_offer,
                "agent_offer": counter_offer,
                "decision": "FINAL_OFFER"
            })

            return {
                "decision": "FINAL_OFFER",
                "offer": counter_offer
            }

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

    def accept_current_offer(self):

        self.accepted = True

        self.history.append({
            "round": self.round_number,
            "customer_offer": self.current_offer,
            "agent_offer": self.current_offer,
            "decision": "ACCEPT"
        })

        return {
            "decision": "ACCEPT",
            "offer": self.current_offer
        }
    def accept_quantity_offer(self):

        if self.quantity_opportunity is None:
            return {
                "decision": "NO_QUANTITY_OFFER"
            }

        opportunity = self.quantity_opportunity

        new_quantity = opportunity["quantity"]
        final_price = opportunity["total_price"]

        # Update the actual cart quantity
        if len(self.cart) == 1:

            self.cart[0]["quantity"] = new_quantity

        # Recalculate the cart
        self.cart_summary = calculate_cart(
            self.cart,
            self.products
        )

        self.original_price = (
            self.cart_summary["total_original_price"]
        )

        self.floor_price = (
            self.cart_summary["total_floor_price"]
        )

        # Quantity deal becomes the current/final offer
        self.current_offer = final_price

        self.accepted = True

        self.quantity_opportunity = None

        self.history.append({
            "round": self.round_number,
            "customer_offer": final_price,
            "agent_offer": final_price,
            "decision": "QUANTITY_ACCEPTED",
            "quantity": new_quantity
        })

        return {
            "decision": "QUANTITY_ACCEPTED",
            "offer": final_price,
            "quantity": new_quantity
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