from hotkeys import Hotkey, norm


def test_norm_aliases():
    assert norm("Left Ctrl") == "ctrl"
    assert norm("AltGr") == "right alt"
    assert norm(None) == ""


def test_combo_with_generic_modifiers():
    hk = Hotkey("ctrl+shift+space", None, None)
    assert hk.satisfied({"right ctrl": 0, "shift": 0, "space": 0})
    assert not hk.satisfied({"ctrl": 0, "space": 0})
    assert hk.involves("right shift")
    assert not hk.involves("a")


def test_right_ctrl_is_specific():
    hk = Hotkey("right ctrl", None, None)
    assert hk.satisfied({"right ctrl": 0})
    assert not hk.satisfied({"ctrl": 0})
