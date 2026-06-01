"""
/anomalies — Detect unusual patterns in sales data.
Checks: hour-level GMV spikes, single-transaction outliers,
unusual discount usage, salesperson GMV concentration.
"""
from fastapi import APIRouter, Request
import pandas as pd
import numpy as np

router = APIRouter()


@router.get("")
async def get_anomalies(request: Request):
    df = request.app.state.loader.df
    anomalies = []

    anomalies.extend(_hourly_gmv_spike(df))
    anomalies.extend(_basket_outliers(df))
    anomalies.extend(_discount_anomaly(df))
    anomalies.extend(_salesperson_concentration(df))
    anomalies.extend(_low_traffic_hours(df))

    return {
        "store": "Brigade_Bangalore",
        "date": "2026-04-10",
        "total_anomalies": len(anomalies),
        "anomalies": anomalies,
    }


def _hourly_gmv_spike(df: pd.DataFrame) -> list:
    hourly = df.groupby("hour")["GMV"].sum()
    mean, std = hourly.mean(), hourly.std()
    out = []
    for hour, val in hourly.items():
        if val > mean + 2 * std:
            out.append({
                "type": "hourly_gmv_spike",
                "severity": "high",
                "hour": int(hour),
                "gmv": float(val),
                "mean_gmv": round(float(mean), 2),
                "z_score": round((val - mean) / std, 2),
                "description": f"Hour {hour}:00 GMV ₹{val:,.0f} is {round((val-mean)/std,1)}σ above mean",
            })
    return out


def _basket_outliers(df: pd.DataFrame) -> list:
    basket = df.groupby("order_id")["GMV"].sum()
    q3, iqr = basket.quantile(0.75), basket.quantile(0.75) - basket.quantile(0.25)
    threshold = q3 + 1.5 * iqr
    out = []
    for order_id, val in basket[basket > threshold].items():
        out.append({
            "type": "large_basket",
            "severity": "medium",
            "order_id": int(order_id),
            "gmv": float(val),
            "threshold": round(float(threshold), 2),
            "description": f"Order {order_id} basket ₹{val:,.0f} exceeds IQR threshold",
        })
    return out


def _discount_anomaly(df: pd.DataFrame) -> list:
    total_gmv = df["GMV"].sum()
    total_discount = df["coupon_amount"].sum()
    disc_pct = total_discount / total_gmv * 100 if total_gmv else 0
    if disc_pct > 5:
        return [{
            "type": "high_discount_rate",
            "severity": "medium",
            "discount_pct": round(disc_pct, 2),
            "description": f"Discount rate {disc_pct:.1f}% exceeds 5% threshold",
        }]
    return []


def _salesperson_concentration(df: pd.DataFrame) -> list:
    sp_gmv = df.groupby("salesperson_name")["GMV"].sum()
    top_share = sp_gmv.max() / sp_gmv.sum() * 100
    if top_share > 50:
        top_sp = sp_gmv.idxmax()
        return [{
            "type": "salesperson_concentration",
            "severity": "low",
            "salesperson": top_sp,
            "gmv_share_pct": round(float(top_share), 2),
            "description": f"{top_sp} accounts for {top_share:.1f}% of GMV — high dependency risk",
        }]
    return []


def _low_traffic_hours(df: pd.DataFrame) -> list:
    hourly_orders = df.groupby("hour")["order_id"].nunique()
    # Flag hours between 10–21 with zero orders
    all_hours = set(range(10, 22))
    active_hours = set(hourly_orders.index.tolist())
    dead_hours = all_hours - active_hours
    out = []
    for h in sorted(dead_hours):
        out.append({
            "type": "zero_traffic_hour",
            "severity": "low",
            "hour": h,
            "description": f"No transactions recorded at {h}:00",
        })
    return out
