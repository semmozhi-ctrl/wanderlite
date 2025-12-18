# API Parity Fixes — Express migration

Summary
- Goal: achieve 1:1 parity for simple GET endpoints between Python FastAPI (`backend/`) and Node Express (`backend_express/`).
- Result: all compared GET endpoints matched in `scripts/api_diff.js` after fixes and proxying.

Key fixes applied
- Auth middleware: normalized error shape to include `detail` and return 403 where Python does.
- `/api/status`: changed Express to return the same empty-array shape (`[]`).
- Bookings/Receipts/AI data: added parity stubs and proxied to Python where exact parity was required.
- `/api/destinations`: fixed proxy handler ordering so the Python payload is returned (was returning an empty array previously).

Current status
- `node scripts/api_diff.js`: all compared GET endpoints matched (green).

Next recommended actions
- Open a PR with the `backend_express` changes and this document.
- Extend the API-diff harness to cover parameterized paths and non-GET endpoints (POST/PUT/DELETE).
- Replace CSV fallbacks with MySQL behind a `USE_MYSQL` feature flag and validate shapes.
- Run CI with the API-diff check and unit/integration tests.

Files touched (high level)
- `backend_express/middleware/auth.js` — auth parity
- `backend_express/index.js` — route registration, `/api/status`
- `backend_express/routes/*` — bookings, receipts, ai, destinations, parity stubs
- `scripts/api_diff.js` — parity harness

If you want, I can open a branch and prepare a PR, then extend the harness to non-GETs next.
