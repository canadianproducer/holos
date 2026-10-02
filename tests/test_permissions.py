import common


def test_access_denied_found_in_exception_chain():
    try:
        try:
            raise PermissionError(13, "Permission denied")
        except PermissionError as inner:
            raise RuntimeError("model load failed") from inner
    except RuntimeError as e:
        assert common.is_access_denied(e)


def test_access_denied_implicit_context():
    try:
        try:
            open("/nonexistent/x")  # FileNotFoundError, not access denied
        except OSError:
            raise ValueError("wrapped") from None
    except ValueError as e:
        assert not common.is_access_denied(e)
    assert not common.is_access_denied(None)


def test_reset_permissions_args_are_recursive_and_continue_on_errors():
    args = common.reset_permissions_args(common.Path("C:/data"))
    assert args[1:] == ["/reset", "/T", "/C", "/Q"]


def test_icacls_is_called_by_full_path():
    assert common.icacls_path().lower().endswith("system32\\icacls.exe") or common.icacls_path().endswith(
        "System32/icacls.exe"
    )
