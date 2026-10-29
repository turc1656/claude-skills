# Writing acceptance tests

Contents: From criterion to specification · Naming · The three layers, with examples · Pragmatic collapse and the split form · Isolation recipes · Choosing the seam · Gherkin repos · Anti-patterns · Gate checklist

## From criterion to specification

An acceptance criterion is a sentence in a story. An executable specification is that sentence made concrete: a named actor, specific example data, one observable outcome, verified through a public interface. One criterion often needs several specifications: the happy path, each named rule, each named failure. Each specification is one test case with one logical assertion.

Expected values come from the story or the domain, never from recomputing what the code will do. If the story says a 5% fee on 200 gives 210, assert 210; never assert `200 * 1.05`.

## Naming

Name the test after the behaviour, as the actor experiences it, so that the approver can check it against the story without reading the body:

- `test_member_sees_latest_rating_on_watched_report`
- `customer can reserve a copy when one is in stock`
- `reservation is refused when no copies remain`

Structure the body as Given / When / Then. Use comments, a helper, or the framework's blocks; the structure matters, the syntax does not.

## The three layers, with examples

The feature: *a customer can place an order for an in-stock title and sees it confirmed; an order for an out-of-stock title is refused.* Seam: the HTTP API.

### Test cases (Python, pytest)

```python
# tests/acceptance/test_ordering.py
from tests.acceptance.support.bookstore import Bookstore


def test_customer_sees_order_confirmed_for_in_stock_title(bookstore: Bookstore) -> None:
    bookstore.stock_title("Refactoring", copies=2)
    bookstore.customer("alice").places_order("Refactoring", quantity=1)
    bookstore.customer("alice").confirms_order_status("confirmed")


def test_order_is_refused_when_title_is_out_of_stock(bookstore: Bookstore) -> None:
    bookstore.stock_title("Refactoring", copies=0)
    bookstore.customer("alice").places_order("Refactoring", quantity=1)
    bookstore.customer("alice").confirms_order_status("refused")
```

No URL, no status code, no table, no JSON key. The reader needs only the story.

### Support module: domain layer and driver together (pragmatic form)

```python
# tests/acceptance/support/bookstore.py
import uuid

from fastapi.testclient import TestClient


def alias(name: str) -> str:
    """Functional isolation: 'alice' becomes 'alice-1f3a' so tests never share data."""
    return f"{name}-{uuid.uuid4().hex[:4]}"


class Bookstore:
    """Domain layer: the story's vocabulary. Every method maps words to driver calls."""

    def __init__(self, driver: "HttpDriver") -> None:
        self._driver = driver
        self._titles: dict[str, str] = {}
        self._customers: dict[str, "Customer"] = {}

    def stock_title(self, title: str, copies: int) -> None:
        self._titles[title] = self._driver.create_title(alias(title), copies)

    def customer(self, name: str) -> "Customer":
        if name not in self._customers:
            self._customers[name] = Customer(self._driver, alias(name), self._titles)
        return self._customers[name]


class Customer:
    def __init__(self, driver: "HttpDriver", customer_id: str, titles: dict[str, str]) -> None:
        self._driver, self._id, self._titles = driver, customer_id, titles
        self._last_order: str | None = None

    def places_order(self, title: str, quantity: int) -> None:
        self._last_order = self._driver.place_order(self._id, self._titles[title], quantity)

    def confirms_order_status(self, expected: str) -> None:
        assert self._last_order is not None, "no order was placed"
        actual = self._driver.order_status(self._last_order)
        assert actual == expected, f"order status is {actual!r}, expected {expected!r}"


class HttpDriver:
    """Protocol driver: the only place that knows the API's shape."""

    def __init__(self, client: TestClient) -> None:
        self._client = client

    def create_title(self, title_id: str, copies: int) -> str:
        response = self._client.post("/titles", json={"id": title_id, "copies": copies})
        response.raise_for_status()
        return response.json()["id"]

    def place_order(self, customer_id: str, title_id: str, quantity: int) -> str:
        payload = {"customer": customer_id, "title": title_id, "quantity": quantity}
        return self._client.post("/orders", json=payload).json()["id"]

    def order_status(self, order_id: str) -> str:
        return self._client.get(f"/orders/{order_id}").json()["status"]
```

A fixture builds the chain: real app, real client, stubbed third parties.

```python
# tests/acceptance/conftest.py
import pytest
from fastapi.testclient import TestClient

from bookstore.app import create_app
from tests.acceptance.support.bookstore import Bookstore, HttpDriver
from tests.acceptance.support.stubs import StubPaymentGateway


@pytest.fixture()
def bookstore() -> Bookstore:
    app = create_app(payment_gateway=StubPaymentGateway())  # stub at the boundary
    return Bookstore(HttpDriver(TestClient(app)))
```

### The same test cases in TypeScript (node:test)

```ts
// tests/acceptance/ordering.test.ts
import { test } from "node:test";
import { bookstore } from "./support/bookstore";

test("customer sees order confirmed for in-stock title", async () => {
  const shop = await bookstore();
  await shop.stockTitle("Refactoring", { copies: 2 });
  await shop.customer("alice").placesOrder("Refactoring", { quantity: 1 });
  await shop.customer("alice").confirmsOrderStatus("confirmed");
});

test("order is refused when title is out of stock", async () => {
  const shop = await bookstore();
  await shop.stockTitle("Refactoring", { copies: 0 });
  await shop.customer("alice").placesOrder("Refactoring", { quantity: 1 });
  await shop.customer("alice").confirmsOrderStatus("refused");
});
```

The support module has the same shape: an `alias()` helper, a domain class, a driver class using `fetch` against the started app, and stubs injected where the app is constructed.

## Pragmatic collapse and the split form

One feature on one protocol: one support module holds the domain layer and the driver, as above. When a second protocol arrives (a CLI, a UI) or a second feature reuses `Bookstore`, split: `support/dsl/bookstore.py` keeps the vocabulary; `support/drivers/http.py` and `support/drivers/cli.py` implement one shared driver interface. The test cases do not change. That unchanged test case is the proof the layering was right.

## Isolation recipes

- **Aliases** for every name a test invents: users, titles, accounts, files. The domain layer owns the mapping; the test case never sees the suffix.
- **Create what you need in the test**, through the domain layer. Never rely on seed data another test or a fixture file put there.
- **Time**: inject a clock or expose a test-only time control; never `sleep`. For asynchronous outcomes, poll a public observable with a bounded timeout: `wait_until(lambda: status() == "confirmed", timeout=5)`.
- **Third parties**: a stub per external system, controllable from the domain layer (`bookstore.payment_provider_will_decline()`), injected where the real client would be.
- **Order independence**: every test passes alone and in any order. Shared state is the bug; randomising the order is not the fix.

## Choosing the seam

The highest public interface that exercises the behaviour end to end:

1. **HTTP API** (or message or gRPC interface) for a service: fast, stable, channel-independent.
2. **CLI** for a command-line tool: run the real entry point in a subprocess; assert on exit code and output.
3. **Public function** for a library: the exported API is the seam; private helpers stay out of the tests.
4. **UI** only for behaviour that lives in the UI: navigation, visibility, accessibility. Use the repo's existing browser tool and assert on what the user sees, through roles and labels rather than selectors. When the page offers neither, match the visible label text and its nearest container, keep that assumption inside the driver, and name it in the approval request: it is where an amendment will most often land.

Verify through the same interface you drove. Reaching into the database to check a row is a side channel: it couples the test to storage and misses the behaviour the user sees. If no public read path exists, that is a finding for the story, not a reason to query the table.

## Gherkin repos

Only when the repo already runs a Gherkin tool (`pytest-bdd`, `behave`, `cucumber-js`, Cucumber-JVM, Reqnroll). The feature file is layer one, the step definitions are the domain layer, and the drivers sit beneath them. Keep steps declarative ("Given a title with 2 copies in stock"), never imperative UI steps ("click the Order button").

## Anti-patterns

- **Protocol leakage**: a test case that names a URL, a selector, a table, a JSON key or a module path.
- **Implementation coupling**: mocking internal collaborators, asserting call counts, testing private functions.
- **Tautology**: the expected value is computed the way the code computes it.
- **Side-channel verification**: querying storage instead of the interface.
- **Horizontal slicing**: writing every test first and every implementation after. One test, one slice, repeat.
- **Timing hacks**: sleeps, or retries that mask flakiness.
- **Unit test in disguise**: an "acceptance test" of a helper nobody outside the module can call.
- **Faking in the driver**: a driver that returns the expected answer without reaching the system. This is why drivers freeze with the tests.

## Gate checklist

Before presenting the approval request:

- [ ] Every criterion maps to specifications, or is listed as not acceptance-testable with a manual check.
- [ ] Each test case reads as behaviour in the story's words, with no protocol detail.
- [ ] Expected values trace to the story, not to the code.
- [ ] Aliases and per-test data, or isolation by construction (own process, own browser context, own stub) stated in the Seam section; nothing depends on order or seed files.
- [ ] Third parties stubbed; the system itself real.
- [ ] Files collected or compiled; not yet run.
- [ ] Run command and working directory named exactly.
