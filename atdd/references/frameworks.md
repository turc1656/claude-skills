# Frameworks and stacks

Contents: Rules of use · Detection · Python · JavaScript and TypeScript · Go · Rust · JVM · .NET · Ruby · PHP · Elixir · Gherkin runners · Monorepos · Reading exit codes

## Rules of use

The repo's own docs (`AGENTS.md`, `CLAUDE.md`, `package.json` scripts, `Makefile`, `justfile`, CI config) are the source of truth for commands. This file holds defaults for when they are silent, plus the gotchas no config file confesses. Record the exact command and working directory in the manifest so red, green and verify run the same thing.

Never add a framework. If the repo has no test runner at all, stop and tell the user; choosing one is their decision.

## Detection

| Signal | Stack |
|---|---|
| `pyproject.toml` with `[tool.pytest...]`, `pytest.ini`, `conftest.py`, `uv.lock`, `poetry.lock` | Python |
| `package.json` with a `test` script; `vitest.config.*`, `jest.config.*`, `playwright.config.*` | JavaScript / TypeScript |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `pom.xml`, `build.gradle`, `build.gradle.kts` | JVM |
| `*.csproj`, `*.sln` | .NET |
| `Gemfile` with rspec, `spec/` | Ruby |
| `composer.json`, `phpunit.xml` | PHP |
| `mix.exs` | Elixir |
| `*.feature` files | a Gherkin runner is in play; find which |

## Python

- Runner: `pytest`, through the project's manager when it has one (`uv run pytest`, `poetry run pytest`, `pipenv run pytest`), else `python -m pytest`.
- One file: `pytest tests/acceptance/test_x.py -q`. One test: `path::test_name` or `-k name`.
- Collection check: `pytest --collect-only -q tests/acceptance/test_x.py`.
- Suite, lint, types: as documented. Common: `pytest`, `ruff check .`, `mypy` or `pyright`.
- Drivers: FastAPI and Starlette `TestClient`, Django `Client`, Flask `test_client()`, `httpx` against a running server, `subprocess.run` for a CLI, `playwright` sync API for a UI when installed.
- Location: `tests/acceptance/`, or beside the repo's existing integration tests. Reuse the fixtures in `tests/conftest.py`.
- Gotchas: settings modules often read `.env` at import; use the repo's fixtures that monkeypatch the environment. SQLite in memory needs `StaticPool` to share one connection across threads. Exit code 5 means nothing collected: a harness problem, not red.

## JavaScript and TypeScript

- Runner: whatever the `test` script in `package.json` runs: `node --test`, `vitest`, `jest`, `mocha`. Package manager from the lockfile: `package-lock.json` npm, `pnpm-lock.yaml`, `yarn.lock`, `bun.lockb`.
- One file: `node --test tests/acceptance/x.test.mjs`; `npx vitest run tests/acceptance/x.test.ts`; `npx jest tests/acceptance/x.test.ts`.
- Compile check: `npx tsc --noEmit`, or the repo's `typecheck` script. With `incremental: true` in `tsconfig.json`, a bare `tsc --noEmit` writes `tsconfig.tsbuildinfo` into the repo; pass `--incremental false`.
- Browser: `npx playwright test tests/acceptance/x.spec.ts` when `playwright.config.*` exists; the config may start a dev server itself through `webServer`. Collection check without running: `npx playwright test --list tests/acceptance/x.spec.ts`. Playwright is the UI seam only.
- Drivers: `fetch` against a started server, `supertest` when already installed, the framework's request handler invoked directly, `child_process` for a CLI, Playwright `page` with role and label locators for the UI.
- Location: follow the repo (`tests/`, `__tests__/`, `e2e/`). Next.js App Router repos often keep node tests in `tests/*.test.mjs` and Playwright specs in `tests/*.spec.ts`.
- Gotchas: `node --test` needs `.mjs` or `"type": "module"`; ESM and CJS mismatches surface as import errors, which are harness failures, not red. Jest's `--findRelatedTests` will not pick acceptance tests; name the file.

## Go

- One package: `go test ./tests/acceptance/... -run TestName -v`. Suite: `go test ./...`. Vet: `go vet ./...`.
- Drivers: `net/http/httptest` for HTTP, `os/exec` for a CLI, public package functions for a library.
- Gotcha: a compile error fails the whole package: harness.

## Rust

- One test file under `tests/`: `cargo test --test acceptance_x`; `cargo test name` filters. Suite: `cargo test`. Lint: `cargo clippy`; format: `cargo fmt --check`.
- Drivers: the crate's public API; `std::process::Command` for a binary (`assert_cmd` only if already a dev-dependency); `reqwest` only if already present.
- Gotcha: exit code 101 on test failure; compile errors are harness.

## JVM

- Maven: `mvn -q test -Dtest=OrderingAcceptanceTest`. Gradle: `./gradlew test --tests "*OrderingAcceptanceTest"`. Suite: `mvn test` or `./gradlew test`.
- Drivers: Spring `MockMvc` or `TestRestTemplate`, `java.net.http.HttpClient`, `ProcessBuilder` for a CLI.

## .NET

- One class: `dotnet test --filter FullyQualifiedName~OrderingAcceptance`. Suite: `dotnet test`.
- Drivers: `WebApplicationFactory<TProgram>` for ASP.NET, `HttpClient`, `Process` for a CLI.

## Ruby

- `bundle exec rspec spec/acceptance/ordering_spec.rb`; suite `bundle exec rspec`. Drivers: Rack::Test; Capybara for the UI when present.

## PHP

- `vendor/bin/phpunit tests/Acceptance/OrderingTest.php`; suite `vendor/bin/phpunit`. Laravel: the HTTP test helpers; Symfony: `WebTestCase`.

## Elixir

- `mix test test/acceptance/ordering_test.exs`; suite `mix test`. Drivers: Phoenix `ConnTest`; `System.cmd` for a CLI.

## Gherkin runners

Use only when already present. `pytest-bdd` (`pytest tests/acceptance/features`), `behave` (`behave features/`), `cucumber-js` (`npx cucumber-js features/ordering.feature`), Cucumber-JVM through the build tool, Reqnroll through `dotnet test`. Step definitions are the domain layer; drivers sit beneath them.

## Monorepos

Find the package that owns the seam and run its commands from its directory; record `--cwd` in the manifest, relative to the repository root and inside it. A feature that crosses packages gets one manifest per seam only if the specifications genuinely differ; usually the highest seam (the API the frontend calls, or the UI) is the one to specify against, with the other package's behaviour reached through it. When the behaviour lives in one package, a sibling deployable is external at its network seam and is stubbed there, the way the repo's existing tests already do it if they do.

## Windows

Write files with LF line endings (Python: `newline="\n"` or bytes; Node: plain strings) and diff with `--strip-trailing-cr`. The lock script normalises CRLF before hashing, but a review diff does not, and one CRLF rewrite turns a small change into a whole-file replacement. Use `python` where `python3` is absent.

## Reading exit codes

Red needs a non-zero exit **and** a failure message that names missing behaviour. A missing public method, symbol, route or command of the system under test is missing behaviour, even when it surfaces as an `AttributeError`, `ImportError` or collection error. Harness failures to recognise: import or compile errors inside the test's own files, "no tests collected" (pytest exits 5), "no tests found", fixture errors, a timeout on startup, a driver exception before the first request. Fix those through `amend` before claiming red.
