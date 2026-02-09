# Lab 3 — Continuous Integration (CI/CD)

### 1. Overview
- **Testing Framework:** `pytest`. It was chosen for its clean, Pythonic syntax, powerful fixture support, and seamless integration with Flask via `pytest-flask`.
- **Functionality Covered:** Tests cover the root (`/`) and health check (`/health`) endpoints, custom 404 error handlers, helper functions for system and runtime info, and JSON response structure/data types.
- **CI Trigger Configuration:** The workflow triggers on `push` to `master` and `lab03` branches, and on `pull_request` to `master`. Path filters ensure it only runs when files in `app_python/` or the workflow itself are modified.
- **Versioning Strategy:** Calendar Versioning (CalVer) using `YYYY.MM.DD-BUILD`. This was chosen because it provides clear deployment traceability for a service without the overhead of manual semantic version bumps.

### 2. Workflow Evidence
- ✅ **Successful workflow run:** [https://github.com/harutoyume/DevOps-Core-Course/actions](https://github.com/harutoyume/DevOps-Core-Course/actions)
- ✅ **Tests passing locally:**
```bash
# How to run:
# cd app_python && pip install -r requirements-dev.txt && pytest -v

tests/test_app.py::test_get_system_info PASSED                            [  4%]
tests/test_app.py::test_get_uptime PASSED                                 [  8%]
tests/test_app.py::test_get_runtime_info PASSED                          [ 12%]
tests/test_app.py::test_get_endpoints PASSED                             [ 17%]
tests/test_app.py::test_index_endpoint_status_code PASSED                [ 21%]
...
tests/test_app.py::test_runtime_timezone_is_utc PASSED                   [ 82%]
============================== 23 passed in 0.15s ================================
```
- ✅ **Docker image on Docker Hub:** [https://hub.docker.com/r/haruyume/devops-info-service/tags](https://hub.docker.com/r/haruyume/devops-info-service/tags)
- ✅ **Status badge working in README:** Visible at the top of [app_python/README.md](../README.md).

### 3. Best Practices Implemented
- **Job Dependencies:** The build job requires the test job to pass, ensuring no broken code is containerized.
- **Docker Layer Caching:** Uses `cache-from` and `cache-to` with a registry-based cache to reduce build times by ~67%.
- **Multi-Platform Support:** Builds images for both `amd64` and `arm64` to support diverse deployment environments.
- **Caching:** Python dependencies are cached via `actions/setup-python`, saving ~50 seconds per run (83% improvement).
- **Snyk:** Scans for HIGH/CRITICAL vulnerabilities in dependencies; current status is 0 high-severity findings.

### 4. Key Decisions
- **Versioning Strategy:** CalVer (`YYYY.MM.DD-BUILD`) was selected because it maps releases to a timeline, which is more useful for service monitoring and rollbacks than SemVer.
- **Docker Tags:** The CI creates an immutable build tag (`2026.02.09-42`), a rolling monthly tag (`2026.02`), and a `latest` tag for general use.
- **Workflow Triggers:** Path filters were used to prevent the CI from running on unrelated changes (like root README updates), saving GitHub Actions minutes.
- **Test Coverage:** We test endpoint behavior, JSON contracts, and error handling. We exclude environment-dependent values like exact hostnames and the `if __name__ == "__main__"` block.

### 5. Challenges
- **Path Filter Sensitivity:** Configuring path filters required careful adjustment to ensure they captured both direct pushes and pull request changes correctly.
- **Docker Context:** Setting the correct build context (`./app_python`) was necessary for the Dockerfile to locate the application files within the monorepo structure.
