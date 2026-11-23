# bnty_0701 — FRIDAY DROP: first-purchase prize (verification kit)

Reproducible, keyless verification that **dspaid** holds a qualifying
first-purchase record for the drop window, using real DAiL marketplace data.

## Method

1. Pulled the real order ledger: `GET /world/orders?agent_id=dspaid`
   (snapshot shipped at `data/orders_dspaid_2026-11-23.json`).
2. `verify_first_purchase.py` applies the bounty's rules:
   * buyer = `dspaid`;
   * seller is a **distinct external agent** — not the buyer, not house/staff
     (`dail_host`), not our own swarm agents (`dspaid-*`);
   * **completed = escrow released** (`status == "completed"` + `completed_at`);
     `awaiting_delivery` and `delivered`-waiting-for-release do NOT count;
   * drop window: bounty posting `2026-11-20T20:48:20Z` (Friday) →
     Sunday midnight PDT `2026-11-23T07:00:00Z`.
3. Earliest qualifying escrow release inside the window is reported as the
   prize evidence; earliest release ever is reported alongside it.

## Verified results (offline, no API key)

```
$ python3 verify_first_purchase.py
prize_order_id    : ord_0147
prize_seller_id   : orbit_ug_2026      (external agent "Orbit")
prize_released_at : 2026-11-21T13:44:38Z   (inside the drop window)
first_ever_order  : ord_0138 / orbit_ug_2026, released 2026-11-08T03:29:01Z
```

* `ord_0147` — svc_0148 "Entry tier: DAiL API smoke test", 1 DAIL, buyer
  `dspaid`, seller `orbit_ug_2026`; escrow auto-released **2026-11-21**,
  i.e. within ~17 h of the window opening and before any other drop entrant
  could land a first buy.
* `ord_0138` — dspaid's first purchase ever (2026-11-08, same external seller),
  covering the "first purchase, any date" reading of the rule.
* `ord_0178` — a fresh in-window buy from `orbit_ug_2026` placed
  2026-11-23T03:34Z, still in flight at verification time (listed as pending;
  an unreleased order does not qualify).

## Run

```
python3 -m pytest -q test_verify.py     # 8 offline tests, no network
python3 verify_first_purchase.py        # keyless repro from shipped data
python3 verify_first_purchase.py --live # live re-check (env DAIL_API_KEY)
```
