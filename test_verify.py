"""Offline tests for verify_first_purchase (no network, no API key)."""
import json
import os

from verify_first_purchase import BUYER, evaluate, escrow_released, is_external_seller

HERE = os.path.dirname(os.path.abspath(__file__))


def shipped_orders():
    with open(os.path.join(HERE, "data", "orders_dspaid_2026-11-23.json"), encoding="utf-8") as fh:
        return json.load(fh)["orders"]


def order(**kw):
    base = {"order_id": "ord_x", "buyer_id": BUYER, "provider_id": "someone_else",
            "status": "completed", "created_at": "2026-11-21T00:00:00+00:00",
            "delivered_at": "2026-11-21T01:00:00+00:00",
            "completed_at": "2026-11-21T02:00:00+00:00"}
    base.update(kw)
    return base


def test_shipped_data_prize_is_in_window_external_release():
    r = evaluate(shipped_orders())
    # ord_0147 (seller orbit_ug_2026) released escrow 2026-11-21, inside the drop window.
    assert r["prize_order_id"] == "ord_0147"
    assert r["prize_seller_id"] == "orbit_ug_2026"
    assert r["prize_released_at"].startswith("2026-11-21")


def test_shipped_data_first_ever_is_ord_0138():
    r = evaluate(shipped_orders())
    # first external purchase ever released for dspaid: ord_0138 on 2026-11-08 (pre-drop).
    assert r["first_ever_order_id"] == "ord_0138"
    assert r["first_ever_seller_id"] == "orbit_ug_2026"


def test_delivered_but_waiting_does_not_count():
    # "delivered" = escrow not yet released, so it must never qualify.
    r = evaluate([order(order_id="ord_d", status="delivered", completed_at=None)])
    assert r["prize_order_id"] is None
    assert r["pending_orders"][0]["order_id"] == "ord_d"


def test_house_and_own_swarm_sellers_do_not_count():
    orders = [
        order(order_id="ord_h", provider_id="dail_host"),
        order(order_id="ord_s", provider_id=BUYER + "-swarm"),
        order(order_id="ord_m", provider_id=BUYER),  # seller == buyer
    ]
    r = evaluate(orders)
    assert r["prize_order_id"] is None and r["first_ever_order_id"] is None


def test_release_outside_window_is_not_prize():
    before = order(order_id="ord_old", completed_at="2026-11-19T12:00:00+00:00")
    after = order(order_id="ord_late", completed_at="2026-11-23T08:00:00+00:00")
    inside = order(order_id="ord_ok", completed_at="2026-11-22T23:30:00+00:00")
    r = evaluate([before, after, inside])
    assert r["prize_order_id"] == "ord_ok"


def test_earliest_in_window_release_wins():
    early = order(order_id="ord_a", completed_at="2026-11-21T01:00:00+00:00")
    late = order(order_id="ord_b", completed_at="2026-11-22T01:00:00+00:00")
    assert evaluate([late, early])["prize_order_id"] == "ord_a"


def test_seller_external_rules():
    assert is_external_seller("orbit_ug_2026", BUYER)
    assert not is_external_seller("dail_host", BUYER)
    assert not is_external_seller("dspaid-swarm", BUYER)
    assert not is_external_seller(BUYER, BUYER)
    assert not is_external_seller("", BUYER)


def test_escrow_released_semantics():
    assert escrow_released(order())
    assert not escrow_released(order(status="awaiting_delivery", completed_at=None))
    assert not escrow_released(order(status="delivered", completed_at=None))
    assert not escrow_released(order(status="disputed"))
