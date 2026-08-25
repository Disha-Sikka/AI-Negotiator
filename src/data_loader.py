import pandas as pd


def load_products(path="data/products.csv"):
    products = pd.read_csv(path)

    # Basic validation
    required_columns = [
        "product_id",
        "product_name",
        "selling_price",
        "cost_price",
        "inventory",
        "inventory_age_days",
        "demand_level",
        "min_margin_pct",
        "max_discount_pct"
    ]

    missing = [
        col for col in required_columns
        if col not in products.columns
    ]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    return products