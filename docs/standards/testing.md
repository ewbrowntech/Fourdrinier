---
description: Testing standards for Fourdrinier
globs:
  - "**/tests/**/*.py"
  - "**/test_*.py"
  - "**/*_test.py"
alwaysApply: false
paths:
  - "**/tests/**/*.py"
  - "**/test_*.py"
  - "**/*_test.py"
---

# Testing Standards

## Table of Contents

- [Scope](#scope)
- [General Expectations](#general-expectations)
  - [Coverage](#coverage)
  - [Independence and Reducing Redundancy](#independence-and-reducing-redundancy)
- [Unit Testing](#unit-testing)
- [Python](#python)
  - [Test Structure](#test-structure)
    - [Title](#title)
    - [Docstrings](#docstrings)
    - [Arrange, Act, Assert](#arrange-act-assert)
    - [Example](#example)
  - [Fixtures, Helpers, and Isolation](#fixtures-helpers-and-isolation)
  - [Async and API Tests](#async-and-api-tests)

## Scope

These rules apply to automated tests in this repository. They complement the
applicable language and application standards; they do not replace them.

## General Expectations

- Add or update tests whenever a change alters observable behavior. A defect
  fix must include a regression test that fails without the fix.
- Test behavior and contracts rather than private implementation details. Tests
  should remain valid when an implementation is refactored without changing its
  public behavior.
- Cover the successful path, relevant failure paths, and meaningful boundary
  conditions. Prefer a small, purposeful set of tests over redundant cases.
- Keep each test independent, deterministic, and readable. Do not rely on test
  execution order, shared mutable state, wall-clock time, external services, or
  ambient machine configuration.
- Name tests after the behavior they establish. A failing test name should make
  the missing or broken behavior clear.
- Assert the outcome that matters to the contract. Avoid assertions unrelated
  to the behavior under test.

### Coverage

The test suite must maintain 100% line and branch coverage.

### Independence and Reducing Redundancy

Tests must be independently executable: no test may depend on another test's
state, side effects, or execution order. Independence does not require splitting
every assertion into a separate test.

Do not write multiple tests with identical Arrange and Act sections solely to
assert different outcomes of the same behavior. Consolidate those assertions
into one test. Keep separate tests when they exercise distinct setup, actions,
scenarios, or behaviors.

While writing or modifying tests, review the affected test set for redundancy.
Consolidate redundant tests before considering the work complete.

## Unit Testing

A unit test must exercise a single unit of code in isolation. Replace every
dependency outside that unit with a mock, fake, stub, or other focused test
double. This requirement includes HTTP clients, databases, filesystems,
third-party services, sibling modules, and lower-level services implemented by
this application.

Unit tests must not perform real network requests, access a real or in-memory
database, read from or write to a real filesystem, or execute dependent
application services. Configure test doubles with only the behavior needed for
the scenario, and assert dependency interactions when those interactions are
part of the unit's contract.

## Python

### Test Structure

Use pytest's plain test functions. Extract a helper only when it improves
clarity across multiple tests.

Use `pytest.mark.parametrize` for the same behavior across distinct inputs.
Give each case a meaningful identifier when pytest's generated description
would not make a failure clear.

#### Title

Name every test using the convention
`test_<unit_under_test>_<number>_<nominal|anomalous>_<condition_being_tested>`,
choosing either `nominal` or `anomalous` for each test. A nominal test covers
expected behavior under valid conditions; an anomalous test covers an error,
invalid input, or exceptional condition.

Use snake case throughout. Name the unit explicitly, assign the test a unique
three-digit number within its module, and describe the specific condition being
exercised.

#### Docstrings

Every test must have a docstring using this format:

```python
"""Test <number> - <Nominal|Anomalous>
Condition: <Brief explanation of the conditions>
Result: <Brief explanation of the expected result>
"""
```

Each test module must have a docstring that identifies the unit it covers. In a
test docstring, use the same three-digit number as the test function name; do
not repeat the unit name. Keep the `Condition` and `Result` descriptions to one
line each when reasonable. Describe exceptions using their type and exact
message, such as `Exception("This code failed!")`, instead of explaining the
exception in prose.

#### Arrange, Act, Assert

Structure every test using the Arrange, Act, Assert pattern. Mark each section
with an `# Arrange`, `# Act`, or `# Assert` comment so the test's setup,
behavior under test, and expected outcome are immediately clear.

Organize each test around setup, one action, and assertions.

#### Example

The following fictional welcome-email example demonstrates the complete
structure of an isolated unit test:

```python
"""Unit tests for application.welcome_email.send_welcome_email."""

from unittest.mock import AsyncMock, Mock

import pytest

from application import welcome_email


async def test_send_welcome_email_001_nominal_user_has_valid_name_and_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 001 - Nominal
    Condition: The user has a valid name and email address
    Result: A personalized welcome email is sent to the user
    """
    # Arrange
    user_name = "Ada"
    user_email = "ada@example.com"
    expected_body = "Welcome, Ada!"
    render_message = Mock(
        spec=welcome_email.render_message,
        return_value=expected_body,
    )
    send_email = AsyncMock(spec=welcome_email.send_email)

    monkeypatch.setattr(welcome_email, "render_message", render_message)
    monkeypatch.setattr(welcome_email, "send_email", send_email)

    # Act
    await welcome_email.send_welcome_email(
        name=user_name,
        email=user_email,
    )

    # Assert
    render_message.assert_called_once_with(user_name)
    send_email.assert_awaited_once_with(
        recipient=user_email,
        subject="Welcome!",
        body=expected_body,
    )
```

### Fixtures, Helpers, and Isolation

Fixtures and helpers can reduce boilerplate, but brevity is not the goal. Use
them when they reduce the cognitive load of maintaining and reviewing tests by
making setup or intent easier to understand.

Inline a fixture or helper when it is rarely reused or when understanding the
abstraction requires more effort than understanding the code it replaces.
Prefer clear, local setup over indirection that merely saves lines.

Use fixtures for reusable setup and dependencies. Keep fixture scope as narrow
as practical, and ensure any resource created by a fixture is cleaned up after
the test.

### Async and API Tests

Write asynchronous tests and fixtures as `async def`; this project configures
pytest-asyncio's automatic mode. Await asynchronous operations directly rather
than introducing event-loop management in individual tests.
