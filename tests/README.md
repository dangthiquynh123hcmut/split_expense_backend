# Test Suite — Split Expense Backend

## Overview

The automated tests are written with **pytest** and **pytest-django**.
They live in this `tests/` directory, completely separate from the application
source code in `src/`.

```
tests/
├── unit/               # Pure-logic tests — no database, no network
│   ├── test_auth_schemas.py
│   ├── test_auth_token_models.py
│   ├── test_debt_simplification.py
│   ├── test_remove_accents.py
│   └── test_transfer_token.py
└── integration/        # Service-layer tests — use an in-memory SQLite DB
    ├── conftest.py     # Shared fixtures (users, groups, events, mocks)
    ├── test_auth_service.py
    ├── test_bank_account_service.py
    ├── test_expense_service.py
    ├── test_friend_service.py
    ├── test_group_service.py
    └── test_wallet_service.py
```

---

## Prerequisites

1. **Python 3.12+** installed.
2. A virtual environment created at `venv/` in the project root (already present).
3. Development dependencies installed:

```powershell
.\venv\Scripts\pip.exe install -r requirements-dev.txt
```

> Integration tests use an **in-memory SQLite** database and
> **LocMemCache**, configured automatically via
> `src/split_expense_system/test_settings.py`.

---

## Running the Tests

All commands below must be run from the project root:
```
e:\Back-end\DATN\split-expense-backend\
```

Activate the virtual environment first (optional — you can also prefix
every command with `.\venv\Scripts\python.exe -m`):

```powershell
.\venv\Scripts\Activate.ps1
```

---

### Run the entire test suite

```powershell
pytest
```

---

### Run only unit tests

```powershell
pytest tests/unit/ -v
```

Unit tests have zero database dependency and complete in under a second.

---

### Run only integration tests

```powershell
pytest tests/integration/ -v
```

pytest-django automatically applies all Django migrations to a fresh
in-memory SQLite database before the session begins.

---

### Run a single file

```powershell
pytest tests/unit/test_debt_simplification.py -v
pytest tests/integration/test_expense_service.py -v
```

---

### Run a single test class or function

```powershell
# Run one class
pytest tests/unit/test_auth_schemas.py::TestRegisterSchemaEmail -v

# Run one function
pytest tests/integration/test_wallet_service.py::TestWalletTransactions::test_send_deducts_balance -v
```

---

### Show full error tracebacks

```powershell
pytest tests/ -v --tb=long
```

### Short tracebacks (faster to scan)

```powershell
pytest tests/ -v --tb=short
```

---

### Coverage report (optional)

Install the coverage plugin once:

```powershell
.\venv\Scripts\pip.exe install pytest-cov
```

Then run:

```powershell
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Configuration

| File | Purpose |
|---|---|
| `pytest.ini` (project root) | Sets `DJANGO_SETTINGS_MODULE`, adds `src/` to `PYTHONPATH`, points `testpaths` to `tests/`. |
| `src/split_expense_system/test_settings.py` | Overrides production settings: SQLite `:memory:` DB, LocMemCache, dummy e-mail backend, MD5 password hasher for speed. |
| `tests/integration/conftest.py` | Shared pytest fixtures: `user_a/b/c`, `rich_user`, `group_with_members`, `event_with_members`, `bank_account`, and mock patches for FCM / e-mail / notifications. |

---

## Test Isolation Guarantees

- **Unit tests** — no Django DB (`@pytest.mark.django_db` is absent); model
  instances are built in memory with `Model.__new__()`.
- **Integration tests** — each test function runs inside a database
  transaction that is rolled back after the test completes, keeping tests
  independent of one another.
- **Cache** — the `clear_cache` fixture in `test_transfer_token.py` calls
  `cache.clear()` before and after every test.
- **External services** — Firebase Cloud Messaging, e-mail sending, and
  notification persistence are replaced by `unittest.mock.patch` mocks
  defined in `conftest.py`.
