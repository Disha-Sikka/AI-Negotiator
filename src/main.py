from data_loader import load_products
from negotiation_engine import initial_offer


products = load_products()

for _, product in products.iterrows():

    offer = initial_offer(product)

    print(
        f"{product['product_name']}: "
        f"Listed ₹{product['selling_price']:.0f} → "
        f"Initial offer ₹{offer:.0f}"
    )