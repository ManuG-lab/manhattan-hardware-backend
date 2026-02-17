import pandas as pd
import re

INPUT_FILE = "shop products - shop.xlsx"
OUTPUT_FILE = "normalized_shop_products.xlsx"


def clean(x):
    if pd.isna(x):
        return None
    return str(x).strip()


def is_size(text):
    if not isinstance(text, str):
        return False
    return bool(re.search(r"(LT|LITRE|ML|KG|KGS)", text.upper()))



def is_category(text):
    if not isinstance(text, str):
        return False
    return text.isupper() and len(text) > 6 and not any(char.isdigit() for char in text)


def normalize_price_list():
    df = pd.read_excel(INPUT_FILE, header=None)
    df = df.map(clean)

    normalized = []
    current_category = None
    current_sizes = []

    for _, row in df.iterrows():
        row = row.tolist()

        # 1. Detect category anywhere in row
        for cell in row:
            if is_category(cell):
                current_category = cell
                current_sizes = []
                break

        # 2. Detect size header row
        sizes = []
        for idx, cell in enumerate(row):
            if is_size(cell):
                sizes.append((idx, cell))
        if sizes:
            current_sizes = sizes
            continue

        # 3. Detect product row
        if current_category and current_sizes:
            # first non-empty string is product name
            product = None
            for cell in row:
                if cell and not is_size(cell):
                    product = cell
                    break

            if not product:
                continue

            for col_idx, size in current_sizes:
                if col_idx < len(row):
                    price = row[col_idx]
                    try:
                        price = float(str(price).replace(",", ""))
                        normalized.append([
                            current_category,
                            product,
                            size,
                            price
                        ])
                    except:
                        pass

    out_df = pd.DataFrame(
        normalized,
        columns=["Category", "Product", "Size", "Price"]
    )

    out_df.to_excel(OUTPUT_FILE, index=False)
    print("Normalized file created:", OUTPUT_FILE)
    print("Total SKUs:", len(out_df))


if __name__ == "__main__":
    normalize_price_list()
