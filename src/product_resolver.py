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

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        return matches[0]

    return None