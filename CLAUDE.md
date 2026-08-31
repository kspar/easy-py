# CLAUDE.md

## What this is

**easy-py** — Python SDK for the Easy/Lahendus learning platform (lahendus.ut.ee, University of Tartu), published on PyPI as `easy-py`. It does two things: logs a user in against Keycloak (OIDC) using a local Flask server plus the system browser, and makes typed REST calls to the core API.

Sibling checkouts:

- `../easy-thonny` — the Thonny plugin (`thonny-lahendus` on PyPI), effectively the only consumer. Has its own CLAUDE.md.
- `../easy` — the platform itself (Kotlin core + web SPA). Wire shapes live in `core/src/main/kotlin/core/ems/service/*.kt` (e.g. `assessments.kt`); the dataclasses in `easy/data.py` mirror them.

| | API | IdP | site / OIDC client id |
|---|---|---|---|
| prod | `ems.lahendus.ut.ee` | `idp.lahendus.ut.ee` | `lahendus.ut.ee` / `lahendus.ut.ee` |
| dev | `dev.ems.lahendus.ut.ee` | `dev.idp.lahendus.ut.ee` | `dev.lahendus.ut.ee` / **`lahendus.ut.ee`** |

Dev runs the newer core. Note the dev client id is *not* `dev.lahendus.ut.ee` — `https://dev.lahendus.ut.ee/config.json` is the authority for each environment's realm and client id.

Issues are YouTrack `EZ-*`. The web UI is a JS SPA, so fetching its HTML gives you nothing — read issues through the guest-readable REST API instead:

```bash
curl -s "https://easy.myjetbrains.com/youtrack/api/issues/EZ-1803?fields=summary,description,comments(text)"
```

## Auth flow — the part that keeps breaking

`RequestUtil.start_auth_in_browser()` binds a **single-threaded** Flask server to `127.0.0.1:<free port>` and opens the browser at `/login`. That endpoint 302s to Keycloak carrying a fresh `state` and a PKCE S256 challenge; Keycloak redirects back to `/login?code=...&state=...`, and the callback exchanges the code for tokens **in Python**, stores them, renders `auth-templates/auth-result.html`, and stops the server. Routes: `/login` (both legs), `/health` (readiness probe), `/shutdown` (POST, used by `Ez.shutdown()`).

Invariants worth knowing before editing any of it:

- **No keycloak-js, deliberately.** The IdP rejects browser-origin token requests from `127.0.0.1` (403 — Web Origins), while the same request without an `Origin` header succeeds. A browser-side adapter cannot complete the exchange without an IdP config change; native code can. Do not reintroduce one.
- **`redirect_uri` must byte-match** between the authorization request and the token exchange. The callback calls `clear_server()` first (which nulls `auth_server_port`), so `port` and `redirect_uri` are captured in the `_create_auth_app` closure. Never rebuild them from `self` inside a handler.
- **Shutdown comes from another thread.** The server is `werkzeug.serving.make_server(..., threaded=False)` run via `serve_forever()`; handlers stop it by starting a thread that calls `server.shutdown()`. Calling it inline deadlocks — the loop cannot exit while the handler is still running.
- **Do not set `threaded=True`.** The pending `state -> code_verifier` dict is unlocked and relies on serialized handlers.
- **Do not poll `/login` for readiness.** It 302s (so a `requests.head` status check fails) and each hit mints a pending state. That is what `/health` is for.
- **Only `code` or `error` in the query marks the callback leg**, and only that leg tears the server down; a plain `/login` GET must never kill an auth in progress.
- **`environ['werkzeug.server.shutdown']` is gone** (removed in Werkzeug 2.1) and is not coming back. Pinning to 2.0.x to keep it is what made the SDK unrunnable on Python 3.12+.
- **`RequestUtil` is not picklable** — it holds the token callbacks, which are closures. Any design that moves the server into a `multiprocessing.Process` dies on Windows spawn. An abandoned 2022 branch tried exactly this.

OIDC endpoints are derived once in `RequestUtil.__init__` from `Ez(..., idp_realm_path='/auth/realms/master')` as `{idp_url}{idp_realm_path}/protocol/openid-connect/{auth,token,logout}`. If Keycloak ever drops the `/auth` prefix (its default since 17), that is a parameter change, not a code change.

Logout sends `client_id` + `post_logout_redirect_uri`; modern Keycloak ignores the legacy `redirect_uri`. No id_token is stored, so Keycloak shows a one-click confirmation page — expected, not a bug. Destination is `Ez(..., logout_redirect_url=...)`, defaulting to `https://{idp_client_name}`.

Tokens are persisted through `retrieve_token`/`persist_token` callbacks keyed by `TokenType` (ACCESS/REFRESH); the default pair is in-memory, and `easy/defaults.py` has file-backed ones.

### Probing the IdP when login breaks

```bash
curl -s -o /dev/null -w "discovery: %{http_code}\n" "https://idp.lahendus.ut.ee/auth/realms/master/.well-known/openid-configuration"
```

A 200 there while login is still broken means the realm endpoints are fine and something client-side moved. To check that loopback redirect URIs are still registered — prod accepts them, **dev currently does not**, which blocks all dev login testing until fixed IdP-side:

```bash
curl -s -o /dev/null -w "authorize: %{http_code}\n" "https://idp.lahendus.ut.ee/auth/realms/master/protocol/openid-connect/auth?client_id=lahendus.ut.ee&redirect_uri=http%3A%2F%2F127.0.0.1%3A12345%2Flogin&response_type=code&scope=openid"
```

200 means accepted; 400 with "Invalid parameter: redirect_uri" means the client's redirect URIs need fixing. `../easy/bin/idp-client-check` probes every URL an OIDC client depends on and is the maintained version of this.

## Data layer

`util.handle_response` instantiates **only the top-level** dataclass. Nested list items reach callers as raw dicts, so the nested dataclasses in `easy/data.py` document the wire shape rather than enforcing it — which also means a drifted nested shape fails silently at the consumer, not here. Keep them in sync with the core's `*Resp` classes. Unknown top-level fields log a warning; missing ones become `None`.

## Dependencies

`flask>=3.0` / `werkzeug>=3.0`, plus `requests`; nothing else (PKCE uses stdlib `secrets`/`hashlib`/`base64`). The code itself runs fine on Werkzeug 2.0 — verified — but the floor is deliberately high:

- **Werkzeug 2.0 cannot run on Python 3.12+ at all.** It calls `ast.Str`, removed in 3.12, while compiling URL rules, so merely constructing a `Flask` app raises `AttributeError`. Thonny 5 bundles Python 3.14.
- A `>=2.0` floor would be counted as *already satisfied* by a broken installed 2.0.3, and pip would leave it in place.

Python floor is 3.9.

## Testing

```bash
python -m unittest discover -s tests -v
```

`tests/test_auth.py` covers the whole auth flow without a browser: `RequestUtil._create_auth_app(port, shutdown_server)` takes the shutdown callable as a parameter, so a test passes a `Mock` and drives the routes through `app.test_client()`. Covered: the RFC 7636 Appendix B challenge vector, the full callback round trip (asserting the verifier's S256 matches the challenge that was sent), user cancel, forged/missing/replayed state, exchange failures, `/health`, endpoint derivation, refresh, logout.

What that cannot reach is the real socket, `serve_forever`, and the shutdown handshake — when touching server lifecycle, exercise those for real: start the server, hit it over HTTP, assert the thread exits.

**Test against Thonny's bundled interpreter, not just a system Python** — that is where the Werkzeug breakage was hiding. Thonny ships its own Python (5.x bundles 3.14); make a venv from the interpreter inside the Thonny installation and run the suite there.

## Release

1. Bump `version` in `setup.py`; keep `../easy-thonny/setup.py`'s `easy-py>=...` pin in step.
2. Clear `build/` before building, or files deleted since the last build leak into the wheel.
   If `egg_info` fails with a file-lock or permission error — common on Windows when a sync client, indexer or antivirus is holding the tree — build from a copy in a plain local directory and move the artifacts back into `dist/`.
3. Publish easy-py **before** thonny-lahendus — the plugin's metadata requires the new SDK.

Both `dist/` folders keep older releases, so `twine upload dist/*` (what `publish.cmd` does) tries to re-upload already-published files and fails. Scope it to the new version:

```bash
python -m twine upload dist/easy_py-0.8.0*
```

## Background

0.8.0 (2026-08) was a rescue release: the IdP upgrade removed the keycloak.js that the login page loaded, and verifying the fix on Thonny 5 turned up a second, independent breakage in the Werkzeug pin — either alone made login impossible. It also refreshed the v4.0 response shapes and added `Student.get_inline_comments()`. [PLAN-EZ-1803-1806.md](PLAN-EZ-1803-1806.md) records the full reasoning, the probe results behind each decision, and what was left to the maintainer.
