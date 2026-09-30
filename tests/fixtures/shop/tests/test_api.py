from shop.api import checkout


def test_checkout():
    assert checkout([("a", 10)])["paid"] == 11.8
