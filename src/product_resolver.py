import re


def normalize(text):
    """
    Convert text into a simple comparable form.
    """

    text = str(text).lower()

    # Replace hyphens and special characters with spaces
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Remove common plural 's'
    words = text.split()
    words = [
        word[:-1] if word.endswith("s") and len(word) > 3 else word
        for word in words
    ]

    return " ".join(words).strip()


def resolve_product(product_name, products):

    query = normalize(product_name)

    # -----------------------------
    # Exact / substring matching
    # -----------------------------

    for _, product in products.iterrows():

        actual_name = normalize(
            product["product_name"]
        )

        if query in actual_name or actual_name in query:

            return {
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "selling_price": float(
                    product["selling_price"]
                ),
                "min_margin_pct": float(
                    product["min_margin_pct"]
                ),
                "max_discount_pct": float(
                    product["max_discount_pct"]
                ),
                "demand_level": product["demand_level"]
            }

    # -----------------------------
    # Token-based matching
    # -----------------------------

    query_words = set(query.split())

    best_product = None
    best_score = 0

    for _, product in products.iterrows():

        actual_name = normalize(
            product["product_name"]
        )

        actual_words = set(actual_name.split())

        common_words = query_words.intersection(
            actual_words
        )

        if len(common_words) == 0:
            continue

        score = len(common_words) / len(query_words)

        if score > best_score:

            best_score = score
            best_product = product

    # Require reasonable similarity
    if best_product is None or best_score < 0.5:
        return None

    return {
        "product_id": best_product["product_id"],
        "product_name": best_product["product_name"],
        "selling_price": float(
            best_product["selling_price"]
        ),
        "min_margin_pct": float(
            best_product["min_margin_pct"]
        ),
        "max_discount_pct": float(
            best_product["max_discount_pct"]
        ),
        "demand_level": best_product["demand_level"]
    }