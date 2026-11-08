"""Synthetic business data for the example app (deterministic; stands in for a warehouse query)."""

import zlib

import numpy as np
import pandas as pd

REGIONS = ["EMEA", "AMER", "APAC"]
CHANNELS = ["Direct", "Partner", "Online"]
YEARS = [2022, 2023, 2024]
#: product -> (category, base daily orders, unit price)
PRODUCTS = {
    "Edge Router": ("Hardware", 9, 420),
    "Smart Switch": ("Hardware", 14, 260),
    "Gateway Pro": ("Hardware", 5, 890),
    "Sensor Kit": ("Hardware", 11, 150),
    "Analytics Suite": ("Software", 7, 640),
    "Security Cloud": ("Software", 10, 380),
    "Dev Toolkit": ("Software", 12, 120),
    "Onboarding": ("Services", 6, 500),
    "Managed Ops": ("Services", 4, 1100),
    "Training": ("Services", 8, 240),
    "Premium Support": ("Support", 9, 300),
    "Standard Support": ("Support", 15, 90),
}


def _build_orders() -> pd.DataFrame:
    """One row per day x region x product x channel."""
    rng = np.random.default_rng(7)
    dates = pd.date_range("2022-01-01", "2024-12-31", freq="D")
    products = list(PRODUCTS)
    base = np.array([PRODUCTS[p][1] for p in products])
    price = np.array([PRODUCTS[p][2] for p in products])
    share, channel_price = np.array([0.30, 0.25, 0.45]), np.array([1.0, 0.9, 1.05])
    progress = np.arange(len(dates)) / len(dates)
    day = (
        (1 + 0.6 * progress)
        * (1 + 0.2 * np.sin(2 * np.pi * (dates.dayofyear.values - 80) / 365.25))
        * np.where(dates.dayofweek.values < 5, 1.0, 0.55)
    )[:, None, None, None]
    # APAC grows fastest
    region = np.array([1.0, 1.5, 0.7])[None, :, None, None] * (
        1 + np.array([0.2, 0.4, 1.2])[None, :, None, None] * progress[:, None, None, None]
    )
    lam = day * region * base[None, None, :, None] * share[None, None, None, :]
    n_orders = rng.poisson(lam)
    revenue = n_orders * price[None, None, :, None] * channel_price[None, None, None, :] * rng.normal(1, 0.08, lam.shape)

    df = pd.MultiIndex.from_product([dates, REGIONS, products, CHANNELS], names=["date", "region", "product", "channel"])
    df = df.to_frame(index=False)
    df["category"] = df["product"].map({p: v[0] for p, v in PRODUCTS.items()})
    df["orders"], df["revenue"] = n_orders.ravel(), revenue.ravel().round(2)
    df["year"] = df["date"].dt.year
    return df


ORDERS = _build_orders()


def orders(region: str, year: int) -> pd.DataFrame:
    df = ORDERS[ORDERS["year"] == year]
    return df if region == "All" else df[df["region"] == region]


def cohorts(region: str, year: int) -> pd.DataFrame:
    """Share of each monthly signup cohort still active k months later (k = 0..12; NaN = not yet observed)."""
    rng = np.random.default_rng(zlib.crc32(f"{region}{year}".encode()))
    decay = {"EMEA": 0.11, "AMER": 0.13, "APAC": 0.09}.get(region, 0.11)
    rows = []
    for month in range(1, 13):
        age = (2024 - year) * 12 + 12 - month  # months of history up to Dec 2024
        quality = 1 + 0.015 * month  # later cohorts retain a little better
        row = {"cohort": pd.Timestamp(year=year, month=month, day=1).strftime("%b %Y")}
        for k in range(13):
            retained = 1.0 if k == 0 else min(1.0, np.exp(-decay * k / quality) * (1 + rng.normal(0, 0.015)))
            row[k] = retained if k <= age else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def order_values(region: str, year: int, channels: list[str]) -> pd.DataFrame:
    """A sample of individual order values per channel (log-normal)."""
    shape = {"Direct": (6.2, 0.6), "Partner": (5.8, 0.7), "Online": (4.9, 0.8)}
    frames = []
    for channel in (c for c in CHANNELS if c in channels):
        rng = np.random.default_rng(zlib.crc32(f"{region}{year}{channel}".encode()))
        frames.append(pd.DataFrame({"channel": channel, "value": rng.lognormal(*shape[channel], 2000)}))
    return pd.concat(frames, ignore_index=True)


def latency(env: str, hours: int) -> pd.DataFrame:
    """Request latency percentiles (ms) in 5-minute buckets."""
    if env == "legacy":
        raise ConnectionError("legacy cluster did not respond within 5s")
    rng = np.random.default_rng(zlib.crc32(env.encode()))
    n = hours * 12
    spikes = (rng.random(n) < 0.02) * rng.uniform(1.5, 3, n)
    p50 = {"production": 42, "staging": 68}[env] * (1 + 0.25 * np.sin(np.arange(n) / 72)) * rng.normal(1, 0.04, n)
    return pd.DataFrame(
        {
            "time": pd.date_range(end="2025-01-01 00:00", periods=n, freq="5min"),
            "p50": p50,
            "p95": p50 * (2.1 + spikes),
            "p99": p50 * (3.4 + 1.5 * spikes),
        }
    )
