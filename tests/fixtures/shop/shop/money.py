def round_cents(x):
    return round(x, 2)


def apply_tax(amount, rate=0.18):
    return round_cents(amount * (1 + rate))
