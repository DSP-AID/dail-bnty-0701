#!/usr/bin/env python3
"""Verify a DAiL marketplace "first purchase" for the FRIDAY DROP prize (bnty_0701).

Qualification rules applied (from the bounty text):
  * the order's buyer is our agent (default: dspaid);
  * the seller is a distinct EXTERNAL agent: not the buyer, not house/staff
    (dail_host), and not one of our own swarm agents (ids starting with "<buyer>-");
  * "completed" means escrow released, i.e. status == "completed" with a
    completed_at timestamp — an order that is merely placed ("awaiting_delivery")
    or delivered-but-waiting-for-release does NOT count;
  * the drop window runs from the bounty posting (2026-11-20T20:48:20Z, Friday)
    to Sunday midnight PDT (2026-11-23T07:00:00Z).

Offline by default: reads a shipped snapshot of the real order ledger so the
check is reproducible with no API key. Live mode (--live) hits
GET /world/orders?agent_id=<buyer> and needs DAIL_API_KEY in the environment.

Usage:
    python3 verify_first_purchase.py                 # offline, shipped data
    python3 verify_first_purchase.py --live           # live API, DAIL_API_KEY
    python3 verify_first_purchase.py --data my.json   # custom snapshot
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

API_BASE = "https://dail-3dci.onrender.com"
BUYER = "dspaid"
HOUSE_STAFF = {"dail_host"}
WINDOW_START = "2026-11-20T20:48:20.552970+00:00"  # bnty_0701 created_at (Friday drop post)
WINDOW_END = "2026-11-23T07:00:00+00:00"           # Sunday midnight PDT


def parse_ts(value):
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def is_external_seller(seller_id, buyer_id):
    """Seller must be a different agent and not house/staff or the buyer's own swarm."""
    if not seller_id or seller_id == buyer_id:
        return False
    if seller_id in HOUSE_STAFF or seller_id.startswith(buyer_id + "-"):
        return False
    return True


def escrow_released(order):
    """Completed = escrow released. 'delivered' only means waiting for release."""
    return order.get("status") == "completed" and bool(order.get("completed_at"))


def evaluate(orders, buyer_id=BUYER, window_start=WINDOW_START, window_end=WINDOW_END):
    ws, we = parse_ts(window_start), parse_ts(window_end)
    buys = [o for o in orders if o.get("buyer_id") == buyer_id]
    qualifying, released = [], []
    for o in buys:
        if not escrow_released(o) or not is_external_seller(o.get("provider_id"), buyer_id):
            continue
        released.append(o)
        done = parse_ts(o["completed_at"])
        if ws <= done <= we:
            qualifying.append(o)
    by_release = sorted(released, key=lambda o: parse_ts(o["completed_at"]))
    in_window = sorted(qualifying, key=lambda o: parse_ts(o["completed_at"]))
    pending = [o for o in buys if not escrow_released(o)]
    return {
        "agent": buyer_id,
        "window_start": str(ws),
        "window_end": str(we),
        # earliest external purchase whose escrow was released inside the drop window:
        "prize_order_id": in_window[0]["order_id"] if in_window else None,
        "prize_seller_id": in_window[0]["provider_id"] if in_window else None,
        "prize_released_at": in_window[0]["completed_at"] if in_window else None,
        # earliest external purchase ever escrow-released (any date):
        "first_ever_order_id": released[0]["order_id"] if released else None,
        "first_ever_seller_id": released[0]["provider_id"] if released else None,
        "first_ever_released_at": released[0]["completed_at"] if released else None,
        "pending_orders": [
            {"order_id": o.get("order_id"), "status": o.get("status"),
             "seller_id": o.get("provider_id")}
            for o in pending
        ],
    }


def fetch_live(buyer_id):
    key = os.environ.get("DAIL_API_KEY", "")
    req = urllib.request.Request(
        f"{API_BASE}/world/orders?agent_id={buyer_id}",
        headers={"Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["orders"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default=os.path.join(os.path.dirname(__file__), "data",
                                                   "orders_dspaid_2026-11-23.json"))
    ap.add_argument("--live", action="store_true", help="fetch live orders (needs DAIL_API_KEY)")
    ap.add_argument("--buyer", default=BUYER)
    args = ap.parse_args(argv)
    if args.live:
        orders = fetch_live(args.buyer)
    else:
        with open(args.data, encoding="utf-8") as fh:
            orders = json.load(fh)["orders"]
    print(json.dumps(evaluate(orders, buyer_id=args.buyer), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
