import uuid
from datetime import datetime, timedelta
import pandas as pd
from database import get_connection

EXCEL = 'normalized_shop_products.xlsx'


def is_number(x):
    try:
        if x is None:
            return False
        float(x)
        return True
    except Exception:
        return False


df = pd.read_excel(EXCEL)

for _, row in df.iterrows():
    category = row["Category"]
    product_name = row["Product"]
    size = row["Size"]
    price = row["Price"]



