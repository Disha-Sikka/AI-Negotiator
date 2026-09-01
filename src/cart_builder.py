from src.product_resolver import resolve_product


def build_cart(request, products):

    cart = []

    for item in request.items:

        product = resolve_product(
            item.item_name,
            products
        )

        if product is not None:

            cart.append({
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "quantity": 1,
                "unit_price": product["selling_price"]
            })

    return cart