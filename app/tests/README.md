# Backend Tests

This directory contains comprehensive tests for the Mobility Health backend API.

## Test Structure

- `conftest.py`: Pytest fixtures and test configuration
- `test_auth_flows.py`: Authentication flow tests (register, login, refresh, logout)
- `test_subscription_e2e.py`: End-to-end subscription flow tests
- `test_sos_flow.py`: SOS flow tests (trigger -> agent reception -> sinistre creation)

## Running Tests

### Run all tests
```bash
pytest app/tests/ -v
```

### Run with coverage (target: 90%)
```bash
pytest app/tests/ -v --cov=app --cov-report=html --cov-report=term-missing --cov-fail-under=90
```

### Run specific test file
```bash
pytest app/tests/test_auth_flows.py -v
```

### Run specific test class
```bash
pytest app/tests/test_auth_flows.py::TestAuthFlows -v
```

### Run specific test
```bash
pytest app/tests/test_auth_flows.py::TestAuthFlows::test_login_success -v
```

### Run by marker
```bash
# Run only auth tests
pytest -m auth -v

# Run only e2e tests
pytest -m e2e -v

# Run subscription tests
pytest -m subscription -v

# Run SOS tests
pytest -m sos -v
```

## Test Coverage

The test suite aims for 90% code coverage and includes:

### Auth Flows (test_auth_flows.py)
- User registration (success, duplicate email/username, invalid email)
- User login (success, wrong password, non-existent user, inactive user)
- Token refresh
- Logout
- Get current user info
- Token expiration handling

### Subscription E2E (test_subscription_e2e.py)
- Complete flow: create project -> choose product -> questionnaire -> payment -> attestation
- Subscription without project
- Inactive product handling
- Non-existent product handling
- Other user's project access control
- Questionnaire creation
- Payment initiation and webhook processing
- Attestation generation

### SOS Flow (test_sos_flow.py)
- Complete SOS flow: trigger -> agent reception -> sinistre creation
- SOS trigger without active subscription
- SOS trigger with specific subscription
- Alert list retrieval (user and operator views)
- Alert detail retrieval
- Access control (users can only see their own alerts)
- Automatic sinistre creation on SOS trigger

## Test Database

Tests use an in-memory SQLite database that is created and destroyed for each test, ensuring test isolation.

## Fixtures

Key fixtures available in `conftest.py`:
- `db`: Database session
- `client`: Test client with database override
- `test_user`: Regular user
- `test_admin`: Admin user
- `test_sos_operator`: SOS operator
- `test_doctor`: Doctor user
- `test_product`: Insurance product factory
- `test_project`: Travel project factory
- `test_hospital`: Hospital
- `auth_headers`: Authentication headers for test user
- `admin_headers`: Authentication headers for admin
- `sos_operator_headers`: Authentication headers for SOS operator

## Dependencies

Required packages (already in requirements.txt):
- pytest
- pytest-asyncio
- httpx (via fastapi TestClient)








<<<<<<< HEAD
=======






>>>>>>> feature/backend-update




