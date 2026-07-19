---
description: Backend application standards for Fourdrinier
globs:
  - "src/backend/**/*.py"
  - "src/backend/pyproject.toml"
  - "src/backend/Taskfile"
alwaysApply: false
paths:
  - "src/backend/**/*.py"
  - "src/backend/pyproject.toml"
  - "src/backend/Taskfile"
---

# Backend Coding Standards

## Table of Contents

- [Scope](#scope)
- [Python Conventions](#python-conventions)
  - [Type Annotations](#type-annotations)
  - [Module Docstrings](#module-docstrings)
  - [Class Docstrings](#class-docstrings)
  - [Function and Method Docstrings](#function-and-method-docstrings)
  - [Helper Functions and Methods](#helper-functions-and-methods)
- [Application Boundaries](#application-boundaries)
- [Persistence and Migrations](#persistence-and-migrations)
- [Evolving This Standard](#evolving-this-standard)

## Scope

These rules apply to application code and Alembic migrations under
`src/backend/`. Read this document before making a backend change. It is
deliberately limited to conventions that are not reliably enforced by tooling;
formatting and static-analysis requirements belong in project configuration
and CI.

## Python Conventions

### Type Annotations

Every function and method, including private and nested callables, must have
type annotations for all parameters and its return value. Use `-> None` when a
callable does not return a value.

Every module-level variable, class attribute, and local variable must have an
explicit type annotation, even when its type is obvious from the assigned
value. Prefer precise, concrete types over `Any`. Reserve `Any` for genuinely
untyped external data at a boundary, then validate or narrow it promptly.

```python
DEFAULT_PORT: int = 22


def host_label(name: str, port: int) -> str:
    label: str = f"{name}:{port}"
    return label
```

### Module Docstrings

Every Python module must begin with a module-level docstring containing the
filename, a blank line, and a brief description of what the module does:

```python
"""
filename.py

Brief description of what the module does.
"""
```

The docstring must be the module's first statement unless a shebang or
source-encoding declaration is required. In new typed application modules, place
`from __future__ import annotations` immediately after the docstring.

### Class Docstrings

Every public class must have a concise docstring describing its purpose and
responsibilities.

### Function and Method Docstrings

Every public function and method must have a docstring that follows PEP 257
conventions and uses Google-style sections. Begin with a concise, imperative
summary line. Add a blank line before further detail, and document the public
contract rather than restating the implementation.

Use the following sections when applicable:

- `Args:` describes each parameter except `self` and `cls`.
- `Returns:` describes the meaning of the returned value. Omit it when the
  function returns only `None`.
- `Raises:` lists exceptions that callers are expected to handle. Do not list
  every exception that could arise from an implementation detail.

```python
def create_host(name: str, address: str) -> Host:
    """Create a host with the supplied connection address.

    Args:
        name: Human-readable name for the host.
        address: Network address used to reach the host.

    Returns:
        The newly created host.

    Raises:
        HostAlreadyExistsError: If a host with the same name already exists.
        InvalidAddressError: If the address cannot be parsed.
    """
    ...
```

### Helper Functions and Methods

Helper functions and methods can reduce duplication, but brevity is not the
goal. Introduce them when they reduce the cognitive load of maintaining and
reviewing the code by making its intent or responsibilities easier to
understand.

Inline a helper when it is rarely reused or when understanding the abstraction
requires more effort than understanding the code it replaces. Prefer clear,
local code over indirection that merely saves lines.

## Application Boundaries

- Keep API routes in `fourdrinier/api/` thin: validate and parse request data,
  call the appropriate CRUD or service layer, and translate expected typed
  failures into the documented HTTP response.
- Keep FastAPI-specific types such as `HTTPException`, `Request`, and
  `Depends` out of CRUD modules and host service modules. Those layers expose
  typed results and domain/transport errors; the API layer owns HTTP mapping.
- Define Pydantic request and response contracts in `fourdrinier/schemas/`. Validate
  untrusted input at that boundary, and use explicit Pydantic response models.

## Persistence and Migrations

- Use SQLAlchemy's async APIs and the request-scoped `AsyncSession` dependency.
  Keep queries and persistence operations in `fourdrinier/db/crud/`, not in
  routes or transport clients.
- Preserve database invariants in SQLAlchemy models and Alembic migrations: use
  constraints, foreign keys, server defaults, and indexes when the invariant
  must hold regardless of the caller. Do not rely on application code alone for
  referential integrity.

## Evolving This Standard

Add a rule only when it is specific, enforceable, and project-relevant. When a
rule can be checked mechanically, prefer adding the formatter, linter, type
checker, or CI check that enforces it instead of expanding this document.
