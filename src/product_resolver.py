import re


def normalize(text):

    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)

    return text.strip()


def resolve_product(product_name, products):

    query = normalize(product_name)

    matches = []

    for _, product in products.iterrows():

        actual_name = normalize(
            product["product_name"]
        )

        if query in actual_name:

            matches.append(product)

    if len(matches) == 0:
        return None

    product = matches[0]

    return {
        "product_id": product["product_id"],
        "product_name": product["product_name"],
        "selling_price": float(product["selling_price"]),
        "min_margin_pct": float(product["min_margin_pct"]),
        "max_discount_pct": float(product["max_discount_pct"]),
        "demand_level": product["demand_level"]
    }