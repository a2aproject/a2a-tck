import os
from typing import Optional

# These will be set by pytest via conftest.py
_sut_url: Optional[str] = None
_test_scope: str = 'core'

def set_config(sut_url: str, test_scope: str = 'core'):
    global _sut_url, _test_scope
    _sut_url = sut_url
    _test_scope = test_scope

def get_sut_url() -> str:
    global _sut_url
    if _sut_url is None:
        _sut_url = os.getenv("SUT_URL")
    if _sut_url is None:
        raise RuntimeError("SUT URL is not configured. Did you forget to pass --sut-url?")
    return _sut_url

def get_test_scope() -> str:
    return _test_scope
