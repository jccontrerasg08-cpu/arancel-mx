# Project TODO

- [ ] Map FastAPI root routes, public static assets, and browser explorer boundaries for unified-site integration.
- [ ] Port the validated arancel-mx marketing and documentation experience to the FastAPI root while preserving `/app`.
- [ ] Preserve explorer browser coverage and add focused root-site regression tests without duplicating existing end-to-end checks.
- [ ] Add one offline Chromium smoke test for the new public root while retaining existing `/app` explorer coverage.
- [x] Add a secure optional GitHub metadata token boundary for live repository activity, with a verified documented fallback.
- [ ] Run full repository validation and create a protected pull request for the unified Vercel deployment.
- [ ] Confirm the Vercel production alias serves the marketing root and the verified `/app` explorer.
- [ ] Keep FastAPI Cloud available as a temporary fallback until Vercel primary validation is complete.
- [ ] Document the Vercel primary cutover criteria before any FastAPI Cloud redirect or retirement decision.
