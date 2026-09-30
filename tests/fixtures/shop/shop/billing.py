from .money import apply_tax


class Invoice:
    def __init__(self, items):
        self.items = items

    def subtotal(self):
        return sum(p for _, p in self.items)

    def total(self):
        return apply_tax(self.subtotal())


def charge(items):
    inv = Invoice(items)
    return inv.total()
