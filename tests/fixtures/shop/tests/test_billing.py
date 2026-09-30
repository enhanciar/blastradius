from shop.billing import charge


def test_charge():
    assert charge([("a", 100)]) == 118.0
