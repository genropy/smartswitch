from smartswitch import Switcher

def test_basic_dispatch():
    book = Switcher("test")

    @book
    def default(a, b): return f"default {a}, {b}"

    @book(typerule={'a': int | float, 'b': str})
    def mixed(a, b): return f"{a}:{b}"

    @book(valrule=lambda a, b: a > 100)
    def big(a, b): return f"BIG {a}"

    assert book('default')('hi', 'x') == "default hi, x"
    assert book()(3, 'a') == "3:a"
    assert book()(200, 0) == "BIG 200"
