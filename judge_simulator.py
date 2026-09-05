import json
import traceback
from pathlib import Path

from src.data_loader import load_products
from src.cart_builder import build_cart
from src.llm_agent import NegotiationRequest, NegotiationItem
from src.negotiation_session import NegotiationSession, MAX_ROUNDS


BASE_DIR = Path(__file__).resolve().parent
CASES_FILE = BASE_DIR / "judge_cases.json"
REPORT_FILE = BASE_DIR / "judge_report.json"


def money(x):
    return round(float(x), 2)

def json_default(obj):
    """
    Converts NumPy/Pandas scalar values such as int64 and float64
    into normal Python values so they can be written to JSON.
    """
    if hasattr(obj, "item"):
        return obj.item()

    raise TypeError(
        f"Object of type {obj.__class__.__name__} "
        f"is not JSON serializable"
    )

def make_request(case):
    return NegotiationRequest(
        intent="NEGOTIATE",
        requested_price=None,
        requested_discount=None,
        items=[
            NegotiationItem(
                item_name=item["item_name"],
                quantity=item.get("quantity", 1)
            )
            for item in case["items"]
        ]
    )


def make_session(case, products):
    """
    IMPORTANT:
    load_products() returns a pandas DataFrame in this project.
    We therefore use the project's real build_cart() instead of iterating
    over the DataFrame manually.
    """
    cart = build_cart(make_request(case), products)

    if not cart:
        raise AssertionError("Cart could not be built.")

    return NegotiationSession(cart, products)


def snapshot(session):
    return {
        "round": session.round_number,
        "current_offer": money(session.current_offer),
        "floor_price": money(session.floor_price),
        "original_price": money(session.original_price),
        "accepted": bool(session.accepted),
        "history_length": len(session.history),
        "cart": [
            {
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "quantity": item["quantity"],
                "unit_price": money(item["unit_price"]),
            }
            for item in session.cart
        ]
    }


def add_turn(result, action, customer_offer, response, session):
    result["transcript"].append({
        "action": action,
        "customer_offer": None if customer_offer is None else money(customer_offer),
        "response": response,
        "state_after": snapshot(session),
    })


def run_case(case, products):
    session = make_session(case, products)

    original = money(session.original_price)
    floor = money(session.floor_price)
    initial = money(session.current_offer)

    result = {
        "id": case["id"],
        "name": case["name"],
        "type": case["type"],
        "status": "PASS",
        "opening": {
            "original_price": original,
            "floor_price": floor,
            "initial_offer": initial,
            "negotiation_mode": session.negotiation_mode,
            "negotiability_score": session.negotiability_score,
        },
        "assertions": [],
        "transcript": [],
    }

    def check(condition, description):
        passed = bool(condition)
        result["assertions"].append({
            "check": description,
            "status": "PASS" if passed else "FAIL",
        })
        if not passed:
            result["status"] = "FAIL"
            raise AssertionError(description)

    # Universal financial invariants
    check(original > 0, "Original cart price is positive")
    check(floor > 0, "Merchant floor is positive")
    check(initial >= floor, "Initial AI offer is at or above merchant floor")
    check(initial <= original, "Initial AI offer does not exceed original cart price")

    t = case["type"]

    if t == "basic":
        check(session.round_number == 0, "New session starts at round 0")
        check(not session.accepted, "New session starts unaccepted")

        # Demonstrate one real safe counteroffer when there is room to negotiate.
        if session.current_offer > session.floor_price:
            customer_offer = (
                session.current_offer + session.floor_price
            ) / 2

            response = session.respond_to_customer_offer(customer_offer)

            add_turn(
                result,
                "CUSTOMER_SAFE_COUNTER",
                customer_offer,
                response,
                session
            )

            check(
                response["offer"] >= session.floor_price,
                "AI response remains above merchant floor"
            )
            check(
                session.round_number == 1,
                "One customer price attempt consumes exactly one round"
            )

    elif t == "quantity":
        check(
            session.quantity_opportunity is not None,
            "Single-product cart exposes a quantity upsell opportunity"
        )

        before_quantity = session.cart[0]["quantity"]
        opportunity_before = dict(session.quantity_opportunity)

        response = session.accept_quantity_offer()

        add_turn(
            result,
            "ACCEPT_QUANTITY_OFFER",
            None,
            response,
            session
        )

        after_quantity = session.cart[0]["quantity"]

        check(
            response["decision"] == "QUANTITY_ACCEPTED",
            "Quantity offer returns QUANTITY_ACCEPTED"
        )
        check(
            after_quantity > before_quantity,
            "Accepted quantity offer increases quantity"
        )
        check(
            session.accepted,
            "Accepted quantity offer closes the negotiation"
        )
        check(
            session.current_offer >= session.floor_price,
            "Accepted quantity deal remains at or above merchant floor"
        )

        result["quantity_evidence"] = {
            "before_quantity": before_quantity,
            "after_quantity": after_quantity,
            "opportunity_before": opportunity_before,
            "final_offer": money(session.current_offer),
            "recalculated_floor": money(session.floor_price),
        }

    elif t == "cart":
        check(
            len(session.cart) >= 2,
            "Cart case contains at least two distinct products"
        )

        customer_offer = 1
        response = session.respond_to_customer_offer(customer_offer)

        add_turn(
            result,
            "MULTI_PRODUCT_LOW_BALL",
            customer_offer,
            response,
            session
        )

        check(
            response["offer"] >= session.floor_price,
            "Low-ball offer cannot push AI below cart floor"
        )
        check(
            session.round_number == 1,
            "Cart negotiation attempt consumes one round"
        )

    elif t == "floor":
        # Generate offers dynamically from the merchant floor.
        # This guarantees that EVERY test offer is genuinely below floor,
        # regardless of whether the product costs ₹800 or ₹7000.
        floor_value = session.floor_price

        low_offers = [
            max(1, floor_value * 0.10),
            max(1, floor_value * 0.20),
            max(1, floor_value * 0.30),
            max(1, floor_value * 0.40),
            max(1, floor_value * 0.50),
        ]

        for round_index, customer_offer in enumerate(
            low_offers,
            start=1
        ):
            response = session.respond_to_customer_offer(
                customer_offer
            )

            add_turn(
                result,
                f"ROUND_{round_index}_BELOW_FLOOR_PRESSURE",
                customer_offer,
                response,
                session
            )

            # Verify test input itself is genuinely below floor.
            check(
                customer_offer < session.floor_price,
                f"Round {round_index}: test offer is genuinely below floor"
            )

            # Most important financial safety check.
            check(
                response["offer"] >= session.floor_price,
                f"Round {round_index}: AI offer stays at or above merchant floor"
            )

            # Rounds 1-4 should reject below-floor offers.
            # Round 5 should lock the negotiation.
            expected_decision = (
                "FINAL_OFFER"
                if round_index == MAX_ROUNDS
                else "BELOW_FLOOR"
            )

            check(
                response["decision"] == expected_decision,
                f"Round {round_index}: expected "
                f"{expected_decision}, got "
                f"{response['decision']}"
            )

        # Exactly five attempts should have been consumed.
        check(
            session.round_number == MAX_ROUNDS,
            "Five below-floor attempts consume exactly MAX_ROUNDS"
        )

        before_round = session.round_number
        before_offer = session.current_offer

        # Try negotiating once more after the limit.
        sixth = session.respond_to_customer_offer(1)

        add_turn(
            result,
            "ROUND_6_AFTER_LIMIT",
            1,
            sixth,
            session
        )

        check(
            session.round_number == before_round,
            "Sixth attempt does not increase the round count"
        )

        check(
            sixth["decision"] == "FINAL_OFFER",
            "Sixth attempt returns FINAL_OFFER"
        )

        check(
            sixth["offer"] == before_offer,
            "AI holds the same final offer after the round limit"
        )

        check(
            sixth["offer"] >= session.floor_price,
            "Held final offer remains at or above merchant floor"
        )

    elif t == "rounds":
        # Exercise genuine COUNTER behavior, not only below-floor rejection.
        # Each customer offer is chosen halfway between the current AI offer
        # and the floor, so it is safe but lower than the AI's current offer.
        for round_index in range(1, MAX_ROUNDS + 1):
            current = session.current_offer
            floor_now = session.floor_price

            check(
                current > floor_now,
                f"Round {round_index}: current offer must be above floor "
                "to exercise a safe counteroffer"
            )

            customer_offer = (current + floor_now) / 2

            response = session.respond_to_customer_offer(customer_offer)

            add_turn(
                result,
                f"ROUND_{round_index}_SAFE_COUNTER",
                customer_offer,
                response,
                session
            )

            check(
                response["offer"] >= floor_now,
                f"Round {round_index}: AI counter remains at or above floor"
            )
            check(
                session.round_number == round_index,
                f"Round counter should equal {round_index}"
            )

            expected_decision = (
                "FINAL_OFFER"
                if round_index == MAX_ROUNDS
                else "COUNTER"
            )

            check(
                response["decision"] == expected_decision,
                f"Round {round_index}: expected {expected_decision}, "
                f"got {response['decision']}"
            )

        final_offer_before = session.current_offer
        round_before = session.round_number

        sixth = session.respond_to_customer_offer(session.floor_price)

        add_turn(
            result,
            "ROUND_6_AFTER_LIMIT",
            session.floor_price,
            sixth,
            session
        )

        check(
            session.round_number == round_before == MAX_ROUNDS,
            "Sixth attempt does not advance past MAX_ROUNDS"
        )
        check(
            sixth["decision"] == "FINAL_OFFER",
            "Sixth attempt returns FINAL_OFFER"
        )
        check(
            sixth["offer"] == final_offer_before,
            "AI holds its final price after the round limit"
        )
        check(
            sixth["offer"] >= session.floor_price,
            "Held final price remains above merchant floor"
        )

        result["round_limit_evidence"] = {
            "max_rounds": MAX_ROUNDS,
            "rounds_used": session.round_number,
            "final_offer": money(session.current_offer),
        }

    elif t == "edge":
        # First prove an extreme low offer stays safe.
        low_response = session.respond_to_customer_offer(1)

        add_turn(
            result,
            "EXTREME_LOW_OFFER",
            1,
            low_response,
            session
        )

        check(
            low_response["offer"] >= session.floor_price,
            "Extreme low offer cannot force a below-floor response"
        )

        # Then use a fresh session and prove the original cart price is accepted.
        fresh = make_session(case, products)
        customer_offer = fresh.original_price

        high_response = fresh.respond_to_customer_offer(customer_offer)

        add_turn(
            result,
            "ORIGINAL_PRICE_OFFER_ON_FRESH_SESSION",
            customer_offer,
            high_response,
            fresh
        )

        check(
            high_response["decision"] == "ACCEPT",
            "Original-price customer offer is accepted"
        )
        check(
            fresh.accepted,
            "Accepted original-price offer closes the negotiation"
        )
        check(
            fresh.current_offer >= fresh.floor_price,
            "Accepted offer remains above merchant floor"
        )

    else:
        raise AssertionError(f"Unknown test type: {t}")

    return result



def main():
    print("\n" + "=" * 78)
    print("AI PAYMENT NEGOTIATOR - EVIDENCE-BASED STRONG AUTOMATED JUDGE")
    print("=" * 78)

    products = load_products()

    print(f"Product source type: {type(products).__name__}")
    print(f"Loaded products: {len(products)}")

    # Load test cases before running them.
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    passed = 0

    for case in cases:
        try:
            result = run_case(case, products)
            passed += 1
            results.append(result)
            print(f"PASS  {case['id']}  {case['name']}")

        except Exception as e:
            results.append({
                "id": case["id"],
                "name": case["name"],
                "type": case.get("type"),
                "status": "FAIL",
                "assertions": [],
                "transcript": [],
                "error": str(e),
                "traceback": traceback.format_exc(),
            })

            print(f"FAIL  {case['id']}  {case['name']}")
            print(f"      {type(e).__name__}: {e}")

    total = len(cases)
    percentage = (passed / total * 100) if total else 0

    # Create the report only AFTER all tests have finished.
    report = {
        "suite": "AI PAYMENT NEGOTIATOR - EVIDENCE-BASED STRONG JUDGE",
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(percentage, 2),
        "status": (
            "READY FOR FINAL DEMO"
            if passed == total
            else "NEEDS REVIEW"
        ),
        "notes": [
            "Uses the project's real build_cart() with the pandas DataFrame returned by load_products().",
            "Every behavioral test records a transcript and post-action session state.",
            "Quantity cases verify actual quantity change, acceptance, and recalculated floor safety.",
            "Floor cases apply repeated below-floor pressure through all five rounds.",
            "Round-limit cases exercise genuine COUNTER responses for rounds 1-4, FINAL_OFFER on round 5, and a sixth blocked attempt.",
            "No Gemini/API calls are used by this judge."
        ],
        "cases": results,
    }

    # Save report after it exists.
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
            default=json_default
        )

    print("\n" + "-" * 78)
    print(f"FINAL SCORE: {passed}/{total}")
    print(f"PASS RATE:   {percentage:.1f}%")

    if passed == total:
        print("STATUS:      READY FOR FINAL DEMO")
    elif percentage >= 90:
        print("STATUS:      EXCELLENT - REVIEW THE FEW FAILURES")
    elif percentage >= 80:
        print("STATUS:      GOOD - FIX FAILED CASES")
    else:
        print("STATUS:      NEEDS REVIEW")

    print("-" * 78)
    print(f"\nDetailed evidence report saved to: {REPORT_FILE.name}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
