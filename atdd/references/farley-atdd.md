# Dave Farley's ATDD, digested

Contents: What an acceptance test is · Properties of a good one · The four-layer model · Isolation · Stubs at the boundary · Ownership and sequence · Red for the right reason · Where this skill is pragmatic · Sources

## What an acceptance test is

An acceptance test is an **executable specification** of the behaviour of the system. It is business-facing: it says what the system does for someone who uses it, in that person's language. It supports programming: it tells the developer when the story is done. Written before the code, it is the automated definition of done, and it exercises the system through its public interfaces in a production-like test environment, so passing means the deployed, configured system behaves as specified, not merely that a function returns a value.

The claim behind the method: if a test says *what* the system does and never *how*, the implementation can change completely and the test still protects the behaviour. That is also why acceptance tests are written first: they capture the requirement before the implementation can bias it.

## Properties of a good acceptance test

Farley's list, with the reason each matters and how this skill applies it.

| Property | Why | In this skill |
|---|---|---|
| **What, not how** | Tests that name endpoints, selectors or tables break on every refactor and specify nothing | Test cases hold only domain language; protocol lives in the driver |
| **Uses the language of the problem domain** | The approver checks it against the story, not against the code | Vocabulary from `CONTEXT.md` and the story; names read as behaviour |
| **Isolated from other tests** | Shared state makes tests order-dependent, flaky and unparallelisable | Aliases, per-test data, no shared mutable fixtures |
| **Repeatable** | A test that passes sometimes measures nothing | No sleeps, no wall clock, no live third parties |
| **Tests any change** | The point is to catch a regression wherever it comes from | Drive the real system through its public interface, end to end |
| **Efficient** | Slow suites get skipped | Highest practical seam, stubs for third parties, no UI when an API exists |

## The four-layer model

```
Test cases          what the system does, in domain language, one behaviour each
     |
Domain layer        the DSL: domain words become actions and checks, with defaults and aliases
     |
Protocol driver     HTTP, CLI, UI, function calls: the only layer that knows how
     |
System under test   real, configured as in production, third parties stubbed
```

Each layer talks only to the one below. The test case cannot see the protocol; the domain layer has no transport assertions and no business logic; the driver knows nothing about which test it serves. The win is **insensitivity to change**: a UI redesign touches the driver, a new API version touches the driver, and the specifications stand. The same test can run against several channels (web UI, mobile, public API) by swapping the driver.

The domain layer carries both actions (`place_order(...)`) and checks (`confirm_order_status(...)`). Checks are still domain-level: the driver fetches and compares raw values, the domain layer names what was compared.

## Isolation

Three kinds, all needed for tests that run in parallel and in any order:

- **Functional isolation**: every test creates its own data under unique aliases. "alice" in the test becomes "alice-7f3a" in the system, so two tests using "alice" never collide. The domain layer does the aliasing; the test case never sees the suffix.
- **Temporal isolation**: no test waits on the clock. The system exposes or injects time, or the test waits for an observable event with a bounded poll. Repeated runs give the same answer.
- **System-level isolation**: the system under test is the only real thing. External systems (payment providers, market data, email) are **stubs** the test controls, so every scenario, including failure of the third party, is reachable and deterministic.

## Stubs at the boundary

Stub what you do not own: the third-party API, the clock, the outside world. Never stub your own modules; that turns an acceptance test into a unit test of a collaboration diagram. The stub sits where the real external system would, speaks the same protocol, and is controllable from the domain layer ("the payment provider will decline the next card"). In a monorepo, another deployable (the backend a frontend calls over HTTP) counts as external at its network seam when the behaviour under test lives in one package; the other package's own behaviour gets its own specifications at its own seam.

## Ownership and sequence

Developers own the acceptance tests. The tests are written before development begins, as the executable form of the acceptance criteria; the developer implements until they pass; a failing acceptance test blocks the release. A separate team lagging behind with tests is the anti-pattern this removes. Translated to this skill: the agent writes the specifications, the user approves them as the definition of done, and the implementation is whatever makes them pass without touching them.

## Red for the right reason

A new test must fail before implementation, and fail because the behaviour is missing. A test that passes immediately specifies nothing: the behaviour exists already, or the test is tautological. A test that fails because its own harness is broken (import error, fixture misconfiguration, driver typo) proves nothing either. Red is evidence only once the failure message names the missing behaviour.

## Where this skill is pragmatic

Farley describes the full model for large systems with many channels. For a single feature on a single protocol, this skill collapses the domain layer and the driver into one support module; the test case stays pure. Split the module when a second protocol or a second feature reuses the vocabulary. The abstraction earns its place by reuse, not by principle.

## Sources

- Farley, *How to Write Acceptance Tests*, Continuous Delivery channel: https://www.youtube.com/watch?v=JDD5EEJgpHU
- Farley, *Why Acceptance Test?*: https://www.linkedin.com/pulse/why-acceptance-test-dave-farley
- Farley, *Acceptance Testing for Continuous Delivery*, QCon 2016 on InfoQ: https://www.infoq.com/presentations/acceptance-testing-cd and the DevDay 2016 slides: https://speakerdeck.com/saec/dave-farley-acceptance-testing-for-continuous-delivery-devday-2016
- Farley, *Continuous Delivery Pipelines* (Leanpub, 2021), the chapters on writing acceptance tests and the four-layer approach: https://leanpub.com/cd-pipelines
- Humble and Farley, *Continuous Delivery* (Addison-Wesley, 2010), chapter 8, Automated Acceptance Testing
- Farley, *Modern Software Engineering* (Addison-Wesley, 2021), the chapters on testability and working in small steps
- CD.Training, *ATDD and BDD: from stories to executable specifications*: https://courses.cd.training/courses/atdd-from-stories-to-executable-specifications
- Optivem's summary of the four layers and external-system stubs: https://journal.optivem.com/p/acceptance-tests-and-external-system-contract-tests
