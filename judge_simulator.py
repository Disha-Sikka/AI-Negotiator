import json
import traceback
from pathlib import Path

from src.data_loader import load_products
from src.cart_builder import build_cart
from src.llm_agent import NegotiationRequest, NegotiationItem
from src.negotiation_session import NegotiationSession, MAX_ROUNDS

BASE_DIR = Path(__file__).resolve().parent
CASES_FILE = BASE_DIR / "judge_cases.json"

def money(x):
    return round(float(x), 2)

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
    cart = build_cart(make_request(case), products)
    if not cart:
        raise AssertionError("Cart could not be built.")
    return NegotiationSession(cart, products)

def check(condition, message):
    if not condition:
        raise AssertionError(message)

def run_case(case, products):
    session = make_session(case, products)
    original = money(session.original_price)
    floor = money(session.floor_price)
    initial = money(session.current_offer)

    # Universal financial invariants
    check(original > 0, f"original price is not positive: {original}")
    check(floor > 0, f"floor is not positive: {floor}")
    check(initial >= floor, f"initial offer {initial} is below floor {floor}")
    check(initial <= original, f"initial offer {initial} exceeds original {original}")

    t = case["type"]

    if t == "basic":
        check(session.round_number == 0, "new session should start at round 0")
        check(not session.accepted, "new session should not be accepted")

    elif t == "quantity":
        check(session.quantity_opportunity is not None,
              "single-item cart should expose a quantity opportunity")
        result = session.accept_quantity_offer()
        check(result["decision"] == "QUANTITY_ACCEPTED",
              f"unexpected quantity decision: {result['decision']}")
        check(session.accepted, "quantity acceptance did not close session")
        check(money(session.current_offer) >= money(session.floor_price),
              "quantity deal went below floor")

    elif t == "cart":
        check(len(session.cart) >= 2, "cart case did not create a multi-item cart")
        check(session.current_offer >= session.floor_price,
              "cart initial offer below floor")

        # A deliberately low offer must never produce an AI price below floor.
        result = session.respond_to_customer_offer(1)
        check(money(result["offer"]) >= money(session.floor_price),
              "cart low-ball caused below-floor AI offer")

    elif t == "floor":
        result = session.respond_to_customer_offer(1)
        check(result["decision"] == "BELOW_FLOOR",
              f"expected BELOW_FLOOR, got {result['decision']}")
        check(money(result["offer"]) >= money(session.floor_price),
              "AI response below floor")

    elif t == "rounds":
        for offer in [1, 100, 500, 1000, 1500, 2000]:
            result = session.respond_to_customer_offer(offer)
            check(session.round_number <= MAX_ROUNDS,
                  f"round exceeded MAX_ROUNDS: {session.round_number}")
            check(money(result["offer"]) >= money(session.floor_price),
                  "round response below floor")

        check(session.round_number == MAX_ROUNDS,
              f"expected {MAX_ROUNDS} rounds, got {session.round_number}")

        before = session.round_number
        result = session.respond_to_customer_offer(1)
        check(session.round_number == before,
              "round count changed after max rounds")
        check(result["decision"] == "FINAL_OFFER",
              f"expected FINAL_OFFER, got {result['decision']}")

    elif t == "edge":
        # Test a low offer, then a normal/high offer on a fresh session.
        low = session.respond_to_customer_offer(1)
        check(money(low["offer"]) >= money(session.floor_price),
              "edge low-offer response below floor")

        session = make_session(case, products)
        high = session.respond_to_customer_offer(original)
        check(high["decision"] == "ACCEPT",
              f"original-price offer should be accepted, got {high['decision']}")
        check(session.accepted, "high offer did not mark accepted")

    return {
        "id": case["id"],
        "name": case["name"],
        "status": "PASS",
        "type": t,
        "original_price": original,
        "floor_price": floor,
        "initial_offer": initial,
    }

def main():
    print("\n" + "=" * 78)
    print("AI PAYMENT NEGOTIATOR - STRONG AUTOMATED JUDGE")
    print("=" * 78)

    products = load_products()
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    earned = 0

    for case in cases:
        try:
            result = run_case(case, products)
            earned += 1
            results.append(result)
            print(f"PASS  {case['id']}  {case['name']}")
        except Exception as e:
            results.append({
                "id": case["id"],
                "name": case["name"],
                "status": "FAIL",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            print(f"FAIL  {case['id']}  {case['name']}")
            print(f"      {e}")

    total = len(cases)
    pct = earned / total * 100 if total else 0

    print("\n" + "-" * 78)
    print(f"FINAL SCORE: {earned}/{total}")
    print(f"PASS RATE:   {pct:.1f}%")
    if earned == total:
        print("STATUS:      READY FOR FINAL DEMO")
    elif pct >= 90:
        print("STATUS:      EXCELLENT - REVIEW THE FEW FAILURES")
    elif pct >= 80:
        print("STATUS:      GOOD - FIX FAILED CASES")
    else:
        print("STATUS:      NEEDS WORK - REVIEW CORE LOGIC")
    print("-" * 78)

    report = {
        "score": earned,
        "total": total,
        "percentage": round(pct, 2),
        "results": results
    }
    report_file = BASE_DIR / "judge_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed report saved to: {report_file.name}")

if __name__ == "__main__":
    main()
