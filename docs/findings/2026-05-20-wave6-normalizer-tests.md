# Wave 6 — `normalizer_v2` Unit Test Coverage

**Date:** 2026-05-20
**Agent:** tester @ basset-hound:normalizer-v2
**Target:** `api/services/normalizer_v2.py` (429 LOC, 0% prior coverage)
**Deliverable:** `tests/test_normalizer_v2.py`

## Public surface area mapped

Module exports tested:

- Dataclass: `NormalizedResultV2` (fields + `to_dict()`)
- Enums: `AmbiguityLevel`, `NormalizationConfidence`
- Class `ConservativeNormalizer` and its public methods:
  - `normalize(value, identifier_type, **hints)` — dispatcher
  - `normalize_phone(phone, country_hint=None)`
  - `normalize_email(email)`
  - `normalize_username(username)`
  - `normalize_domain(domain)`
  - `normalize_url(url)`
  - `normalize_ip(ip)`
  - `normalize_crypto(address)`
  - `normalize_mac_address(mac)`
  - `normalize_date(date_str, format_hint=None)`
  - `normalize_currency(amount_str, currency_hint=None)`
- Singleton helpers: `get_normalizer_v2()`, `reset_normalizer_v2()`

Private regex constants and `COUNTRY_CODES` / `CURRENCY_SYMBOLS` maps are
exercised indirectly via the public methods (not directly tested — per task spec).

## Test count

**70 tests collected** across 13 test classes. Verified via
`pytest --collect-only` (no execution performed in this work zone).

## Coverage strategy

- One `@pytest.mark.unit`-marked class per public entry point (matches the v1
  test file pattern in `tests/test_normalizer.py`).
- Each method: empty/invalid input + happy path + 1-2 edge cases.
- `pytest.mark.parametrize` used for separator variations on phone and MAC
  inputs, and for length validation on phone numbers.
- Ambiguity-focused tests assert the v2-specific contract (the v2 rewrite's
  raison d'être): phones without country code are flagged `HIGH`/`needs_review`,
  ambiguous dates carry `possible_interpretations`, and ambiguous currency
  symbols list candidate ISO codes.
- Hint-resolution tests verify each hint kwarg (`country_hint`, `format_hint`,
  `currency_hint`) clears ambiguity and is reflected in `hints_used`.
- Singleton helpers tested for identity and reset behavior.
- Pure unit isolation: no fixtures from `conftest.py`, no Neo4j/Redis/network,
  fresh `ConservativeNormalizer()` per test via local `normalizer` fixture.
- The only external import is `api.models.orphan.IdentifierType` (pure enum,
  no side effects).

## Notes

Assertions reflect the documented intent per docstrings; not all have been
verified to pass against actual runtime behavior (per task: collection-only
verification). Any divergence between docstring promises and implementation
will surface on first real test run and is itself useful signal.
