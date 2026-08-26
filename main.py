from src.data_loader import load_products
from src.negotiability import calculate_negotiability_score


products = load_products()


for _, product in products.iterrows():

    score = calculate_negotiability_score(product)

    print(
        f"{product['product_name']}: "
        f"Negotiability = {score}/100"
    )