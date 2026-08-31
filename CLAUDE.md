# CLAUDE.md

## What this is

**easy-py** — Python SDK for the Easy/Lahendus educational platform (lahendus.ut.ee, University of Tartu). Published on PyPI as `easy-py`. Handles Keycloak (OIDC) authentication via a local Flask server + system browser, and typed REST calls to the core API.

Related local checkouts (siblings of this directory):

- `../easy-thonny` — the Thonny plugin (`thonny-lahendus` on PyPI) that consumes this SDK. Its student-facing UI calls `Ez.student.*`.
- `../easy` — the platform itself (Kotlin core + web SPA). API response shapes live in `core/src/main/kotlin/core/ems/service/` (e.g. `assessments.kt`); the SDK's dataclasses in `easy/data.py` mirror them.

Environments: prod `ems.lahendus.ut.ee` / `idp.lahendus.ut.ee` / site `lahendus.ut.ee`; dev `dev.ems.lahendus.ut.ee` / `dev.idp.lahendus.ut.ee` / site `dev.lahendus.ut.ee` (dev runs the newer core). Issue tracker: YouTrack `EZ-*` at easy.myjetbrains.com (guest-readable via REST API: `/youtrack/api/issues/EZ-XXXX?fields=summary,description,comments(text)`).

## Architecture notes

- **Auth flow** (`easy/ez.py`, `RequestUtil`): `start_auth_in_browser()` starts a **single-threaded** Flask server on `127.0.0.1:<random port>` and opens the browser at `/login`, which 302s to Keycloak with a per-open `state` + PKCE S256 challenge. Keycloak redirects back to `/login?code=...&state=...`; the callback exchanges the code for tokens **in Python** (no browser JS, no CORS) and shuts the server down. Readiness is polled on `/health`.
  - The IdP **rejects browser-origin token requests from 127.0.0.1** (Web Origins), which is why there is no keycloak-js here — do not reintroduce it.
  - The callback closure captures `port`/`redirect_uri` at server start; `clear_server()` nulls `self.auth_server_port` before the token exchange, so never rebuild the redirect URI from `self` inside handlers (it must byte-match the authorization request).
  - The server is created with `werkzeug.serving.make_server(..., threaded=False)` and run via `serve_forever()` in a thread; handlers stop it by calling `server.shutdown()` **from another thread** (calling it inline would deadlock, since the loop cannot exit while the handler is running). Do not switch to `threaded=True` — the pending-state dict and teardown rely on serialized handlers.
  - It does **not** use `environ['werkzeug.server.shutdown']` any more: that hook was removed in Werkzeug 2.1, and pinning to 2.0.x to keep it made the SDK unusable on Python 3.12+.
- **OIDC endpoints** are derived from the `Ez(..., idp_realm_path='/auth/realms/master')` parameter: `{idp_url}{idp_realm_path}/protocol/openid-connect/{auth,token,logout}`. If the IdP ever drops the `/auth` prefix (Keycloak's default since 17), it's a parameter change, not a code change.
- **Logout** uses `client_id` + `post_logout_redirect_uri` (modern Keycloak ignores the legacy `redirect_uri`). No id_token is stored, so Keycloak shows a one-click confirmation page. Target configurable via `Ez(..., logout_redirect_url=...)`.
- **Token storage**: `retrieve_token`/`persist_token` callbacks keyed by `TokenType` (ACCESS/REFRESH); defaults are in-memory. `easy/defaults.py` has file-based implementations.
- **`util.handle_response`** instantiates only the **top-level** dataclass; nested list items stay raw dicts. The nested dataclasses in `easy/data.py` are documentation of the wire shape — keep them in sync with the core's `*Resp` classes.

## Dependency floors that matter

`flask>=3.0` / `werkzeug>=3.0`. The code itself works fine on Werkzeug 2.0 as well (verified), but the floor is deliberately 3.0 for two reasons:

- **Werkzeug 2.0 cannot run on Python 3.12+ at all.** It calls `ast.Str`, removed in 3.12, while compiling URL rules — so merely constructing a `Flask` app raises `AttributeError`. Thonny 5 bundles Python 3.14, where the old pin was fatal.
- A looser floor (`>=2.0`) would be considered *already satisfied* by an installed, broken 2.0.3 and pip would leave it in place.

No other third-party deps; PKCE uses stdlib (`secrets`, `hashlib`, `base64`).

Python floor is 3.9 (was 3.7, which the Flask 3 stack cannot honour).

**When touching anything in this area, test against Thonny's own interpreter**, not just a local Python:

```bash
"C:/Program Files/Thonny/python.exe" -m venv venv314
```

## Commands

```bash
# Tests (stdlib unittest; Flask required, already in deps)
python -m unittest discover -s tests -v

# Build + publish (Windows batch scripts; clean build/ first so deleted files don't leak into the wheel)
build.cmd
publish.cmd
```

`test.py` is a manual, interactive smoke script (opens a real browser against the hosts configured at the bottom of the file).

## Release / versioning gotchas

- easy-py: bump `setup.py` version; `../easy-thonny/setup.py` pins `easy-py>=...` — keep in sync.
- thonny-lahendus (the plugin) **must** be versioned with exactly three numeric components, and **only a major bump** makes installed plugins prompt the user to update. The installed 9.2.0 generation parses the published version with `major, minor, patch = version.split(".")` and crashes on anything else, so this constraint holds for as long as 9.2.0 clients exist — even though 10.0.0's own checker is now tolerant.
- Publish easy-py before thonny-lahendus.
- Building from the Dropbox working tree can fail with `WinError 5` (Dropbox holds locks during `egg_info`). Build from a copy outside Dropbox and move the artifacts back into `dist/`.

## Current state (2026-08-30)

Implemented here: EZ-1803 (login broken by IdP upgrade) and the Python 3.14 fallout found while verifying it (Werkzeug pin, see above); EZ-1804 and EZ-1806 data shapes. EZ-1804/1805/1806 rendering and the `pkg_resources` startup crash live in `../easy-thonny`.

Built and verified, not published: `dist/easy_py-0.8.0*` and `../easy-thonny/dist/thonny_lahendus-10.0.0*`, installed together with Thonny 5 into a clean Python 3.14 venv.

See [PLAN-EZ-1803-1806.md](PLAN-EZ-1803-1806.md) for the full plan, verification status, and what remains (PyPI releases, manual browser verification, dev-IdP client fix by kspar). The matching plugin change in `../easy-thonny` is not committed yet; its ready-to-use commit message is `../easy-thonny/COMMIT_MESSAGE.txt`.
