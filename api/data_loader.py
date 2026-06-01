"""Loads and pre-processes the Brigade Road sales CSV."""
import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)

DATA_PATH = os.environ.get("DATA_PATH", "data/sales_10_april_2026.csv")


class DataLoader:
    def __init__(self, path: str = DATA_PATH):
        self.path = path
        self.df: pd.DataFrame = pd.DataFrame()

    def load(self):
        self.df = pd.read_csv(self.path)
        self._clean()
        logger.info("Data loaded and cleaned")

    def _clean(self):
        df = self.df
        df["order_date"] = pd.to_datetime(df["order_date"], dayfirst=True)
        df["order_time"] = pd.to_datetime(df["order_time"], format="%H:%M:%S").dt.time
        df["hour"] = pd.to_datetime(df["order_time"].astype(str)).dt.hour
        df["GMV"] = pd.to_numeric(df["GMV"], errors="coerce").fillna(0)
        df["NMV"] = pd.to_numeric(df["NMV"], errors="coerce").fillna(0)
        df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(0).astype(int)
        df["coupon_amount"] = pd.to_numeric(df["coupon_amount"], errors="coerce").fillna(0)
        self.df = df
