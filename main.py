from src.data_loader import load_products
from src.negotiation_session import NegotiationSession


products = load_products()


cart = [
    {
        "product_id": "P002",
        "quantity": 1
    },
    {
        "product_id": "P003",
        "quantity": 1
    },
    {
        "product_id": "P007",
        "quantity": 1
    }
]


session = NegotiationSession(
    cart,
    products
)


print("\n===== NEGOTIATION START =====")

print(
    f"Original price: "
    f"₹{session.original_price:.2f}"
)

print(
    f"Merchant floor: "
    f"₹{session.floor_price:.2f}"
)

print(
    f"Initial AI offer: "
    f"₹{session.current_offer:.2f}"
)


customer_offers = [
    5500,
    5200,
    5000,
    4800,
    4600
]


for customer_offer in customer_offers:

    print(
        f"\nCustomer: "
        f"₹{customer_offer:.2f}"
    )

    response = session.respond_to_customer_offer(
        customer_offer
    )

    print(
        f"Agent: "
        f"{response['decision']} → "
        f"₹{response['offer']:.2f}"
    )

    if response["decision"] == "ACCEPT":
        break