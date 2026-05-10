"""
Root conftest.py – loaded by pytest before any test file is imported.

Patches firebase_admin at the sys.modules level so that FCMService (which
initialises Firebase at module-level import time) does not attempt to read
firebase.json from disk.  The mock makes firebase_admin.get_app() return a
MagicMock instead of raising ValueError, so _initialize_firebase() exits the
early-return branch and never calls credentials.Certificate().
"""

import sys
from unittest.mock import MagicMock


# Only patch when firebase_admin hasn't been imported yet (i.e. in CI where
# the real firebase.json doesn't exist).  Locally, if firebase_admin is
# already loaded with a real app, leave it alone.
if "firebase_admin" not in sys.modules:
    _mock = MagicMock()
    sys.modules["firebase_admin"] = _mock
    sys.modules["firebase_admin.credentials"] = _mock
    sys.modules["firebase_admin.messaging"] = _mock
