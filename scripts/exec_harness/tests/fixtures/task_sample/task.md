---
ticket: TFIX
base_sha: 0123456789abcdef0123456789abcdef01234567
base_branch: dev
branch: feature/TFIX-characterization
steps:
  - step1.md
  - step2.md
seam_guards:
  - S-TFIX characterization guard
dont_touch:
  - backend/
  - frontend/
---

Characterize the current execute harness dry-run contract.
Preserve prompt boundaries and the declared fixture ordering.
Use this fixture only for deterministic, dependency-free tests.
