"""Generate a synthetic labelled ticket dataset.

Real support tickets can't be published, so this builds a realistic stand-in:
the same categories and priorities used in the DMS/SFA support flow, with
varied phrasing, typos and mixed-language text of the kind field users write.
"""

import random
from pathlib import Path

import pandas as pd

random.seed(42)

# category -> (priority, list of phrasings)
TEMPLATES = {
    "PJP_MAP": ("P1", [
        "pjp map not showing for beat {beat}",
        "PJP not visible in app for user {user}",
        "beat plan missing on map, {user} cannot start day",
        "pjp mapping issue - outlets not loading on route",
    ]),
    "GRN_STUCK": ("P1", [
        "GRN stuck for invoice {inv} since morning",
        "grn not processing, distributor {db} unable to receive stock",
        "goods receipt pending, stock not updating for {db}",
        "GRN failed in DMS, invoice {inv} still open",
    ]),
    "USER_CREATION": ("P2", [
        "please create user id for new SO {user}",
        "new user creation request for {db}",
        "need login created for sales officer joining {beat}",
        "user id not created yet for {user}, pending 2 days",
    ]),
    "LOGIN_ISSUE": ("P2", [
        "unable to login in app, invalid credentials error",
        "{user} cannot login, otp not received",
        "login failing after app update",
        "app showing session expired again and again for {user}",
    ]),
    "OUTLET_NOT_VISIBLE": ("P2", [
        "outlet not visible in {user} app after creation",
        "new outlet created but not showing in beat {beat}",
        "outlets missing from route for distributor {db}",
        "shop not appearing in app even after sync",
    ]),
    "BEAT_CHANGE": ("P3", [
        "change beat for outlet in {beat}",
        "beat modification required for {user}",
        "please shift outlets from {beat} to new beat",
        "beat reassignment request for distributor {db}",
    ]),
    "SCHEME_MAIL": ("P4", [
        "scheme mail not received for this month",
        "scheme not applied on invoice {inv}",
        "please share scheme details for {db}",
        "discount scheme missing in app for {beat}",
    ]),
    "INVENTORY_ADD": ("P5", [
        "add new sku to inventory for {db}",
        "inventory addition request for distributor {db}",
        "please add stock of new product in DMS",
        "opening stock entry needed for {db}",
    ]),
}

NOISE = ["", " pls help", " urgent", " kindly do needful", " asap",
         " same issue since yesterday", " thanks", " plz check"]


def make_rows(n_per_class: int = 150) -> pd.DataFrame:
    rows = []
    for category, (priority, templates) in TEMPLATES.items():
        for _ in range(n_per_class):
            text = random.choice(templates).format(
                beat=f"B{random.randint(1, 60)}",
                user=f"SO{random.randint(100, 999)}",
                db=f"DB{random.randint(1000, 9999)}",
                inv=f"INV{random.randint(10000, 99999)}",
            )
            text += random.choice(NOISE)
            if random.random() < 0.15:          # some tickets arrive in caps
                text = text.upper()
            rows.append({"text": text, "category": category, "priority": priority})
    return pd.DataFrame(rows).sample(frac=1, random_state=42).reset_index(drop=True)


if __name__ == "__main__":
    df = make_rows()
    out = Path("data/tickets.csv")
    out.parent.mkdir(exist_ok=True)
    df.to_csv(out, index=False)
    print(f"wrote {len(df)} rows to {out}")
    print(df["category"].value_counts())
    print(df.head(5).to_string(index=False))