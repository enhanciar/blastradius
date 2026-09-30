from shop import billing


def checkout(cart):
    return {"paid": billing.charge(cart)}


def health():
    return "ok"
