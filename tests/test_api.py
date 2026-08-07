"""Offline API test suite. No network access, no real LLM calls."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from api.core.config import APISettings, hash_api_key
from api.main import create_app
from api.models.response import JobAccepted
from api.services.comparison import ComparisonService
from api.services.jobs import JobManager
from api.services.registry import ConsumerAdapter, ConsumerRegistry

VALID_KEY = "test-api-key-123"


def make_settings(**overrides) -> APISettings:
    base = dict(
        auth_disabled=True,
        request_timeout_seconds=30,
        rate_limit="1000/minute",
        producer_rate_limit="1000/minute",
        app_version="test",
        git_sha="deadbeef",
        build_time="2026-08-06T00:00:00Z",
    )
    base.update(overrides)
    return APISettings(**base)


@contextlib.contextmanager
def api_client(settings: APISettings | None = None):
    app = create_app(settings or make_settings())
    # raise_server_exceptions=False: error ENVELOPES (not client-side raises)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, app


class FakeBrief:
    def brief(self, question, max_docs, request_id):
        return {"answer": {"current_situation": "x"}, "documents_used": ["nato"]}


class FakeAnalysis:
    def analyze(self, question, max_docs, request_id):
        return {"critical_analysis": {"assumptions": []}}


class FakeCompare:
    async def compare(self, question, max_docs, request_id):
        return {"question": question, "comparison": {"shared_documents": []}}


class FakeJobService:
    def __init__(self) -> None:
        self.submitted: list = []

    def submit_update(self, request):
        self.submitted.append(request)
        return JobAccepted(
            job_id="fake-job-1",
            job_type="producer.update",
            status="pending",
            created_at="2026-08-06T00:00:00Z",
        )

    def submit_update_all(self, request):
        return JobAccepted(
            job_id="fake-job-2",
            job_type="producer.update_all",
            status="pending",
            created_at="2026-08-06T00:00:00Z",
        )


def install_fakes(app) -> None:
    app.state.briefing_service = FakeBrief()
    app.state.analysis_service = FakeAnalysis()
    app.state.comparison_service = FakeCompare()


def wait_for_job(client: TestClient, job_id: str, timeout: float = 5.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        record = client.get(f"/api/v1/jobs/{job_id}").json()
        if record["status"] in ("succeeded", "failed"):
            return record
        time.sleep(0.05)
    raise AssertionError("job did not finish in time")


class ApiConfigLoadingTests(unittest.TestCase):
    """Regression: backend must resolve OKF_API_KEYS from env or .env."""

    def _dotenv(self, content: str):
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name) / ".env"
        path.write_text(content, encoding="utf-8")
        self.addCleanup(tmp.cleanup)
        return path

    def test_keys_loaded_from_dotenv(self) -> None:
        from api.core.config import load_settings

        dotenv = self._dotenv("OKF_API_KEYS=alpha-key\n")
        settings = load_settings(env={}, dotenv_path=dotenv)
        self.assertEqual(settings.api_key_hashes, {hash_api_key("alpha-key")})
        self.assertTrue(settings.auth_configured)

    def test_multiple_comma_separated_keys(self) -> None:
        from api.core.config import load_settings

        dotenv = self._dotenv("OKF_API_KEYS=alpha-key, beta-key ,gamma-key\n")
        settings = load_settings(env={}, dotenv_path=dotenv)
        self.assertEqual(len(settings.api_key_hashes), 3)
        self.assertIn(hash_api_key("beta-key"), settings.api_key_hashes)

    def test_environment_overrides_dotenv(self) -> None:
        from api.core.config import load_settings

        dotenv = self._dotenv("OKF_API_KEYS=from-file\n")
        settings = load_settings(env={"OKF_API_KEYS": "from-env"}, dotenv_path=dotenv)
        self.assertEqual(settings.api_key_hashes, {hash_api_key("from-env")})

    def test_missing_keys_everywhere_is_not_configured(self) -> None:
        from api.core.config import load_settings

        settings = load_settings(env={}, dotenv_path=None)
        self.assertFalse(settings.auth_configured)

    def test_plaintext_keys_never_stored(self) -> None:
        from api.core.config import load_settings

        dotenv = self._dotenv("OKF_API_KEYS=super-secret-value\n")
        settings = load_settings(env={}, dotenv_path=dotenv)
        self.assertNotIn("super-secret-value", settings.api_key_hashes)


class AuthenticationTests(unittest.TestCase):
    def _settings(self) -> APISettings:
        return make_settings(auth_disabled=False, api_key_hashes={hash_api_key(VALID_KEY)})

    def test_missing_key(self) -> None:
        with api_client(self._settings()) as (client, app):
            install_fakes(app)
            r = client.post("/api/v1/brief", json={"question": "q"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["error"]["code"], "UNAUTHORIZED")

    def test_invalid_key(self) -> None:
        with api_client(self._settings()) as (client, app):
            install_fakes(app)
            r = client.post(
                "/api/v1/brief", json={"question": "q"}, headers={"Authorization": "Bearer wrong"}
            )
        self.assertEqual(r.status_code, 401)

    def test_valid_key(self) -> None:
        with api_client(self._settings()) as (client, app):
            install_fakes(app)
            r = client.post(
                "/api/v1/brief",
                json={"question": "q"},
                headers={"Authorization": f"Bearer {VALID_KEY}"},
            )
        self.assertEqual(r.status_code, 200)

    def test_health_open_without_key(self) -> None:
        with api_client(self._settings()) as (client, _):
            self.assertEqual(client.get("/api/v1/health").status_code, 200)

    def test_keys_stored_hashed_only(self) -> None:
        settings = make_settings(api_key_hashes={hash_api_key(VALID_KEY)})
        self.assertNotIn(VALID_KEY, settings.api_key_hashes)
        self.assertIn(hash_api_key(VALID_KEY), settings.api_key_hashes)


class MiddlewareTests(unittest.TestCase):
    def test_request_id_generated_and_echoed(self) -> None:
        with api_client() as (client, _):
            generated = client.get("/api/v1/health")
            echoed = client.get("/api/v1/health", headers={"X-Request-ID": "my-id-42"})
        self.assertEqual(len(generated.headers["x-request-id"]), 32)
        self.assertEqual(echoed.headers["x-request-id"], "my-id-42")

    def test_timeout_returns_504(self) -> None:
        class SlowBrief:
            def brief(self, q, m, rid):
                time.sleep(1.5)
                return {}

        with api_client(make_settings(request_timeout_seconds=1)) as (client, app):
            install_fakes(app)
            app.state.briefing_service = SlowBrief()
            r = client.post(
                "/api/v1/brief",
                json={"question": "q"},
                headers={"Authorization": "Bearer timeout-identity"},
            )
        self.assertEqual(r.status_code, 504)
        self.assertEqual(r.json()["error"]["code"], "UPSTREAM_TIMEOUT")

    def test_rate_limiting(self) -> None:
        with api_client(make_settings(rate_limit="2/minute")) as (client, app):
            install_fakes(app)
            headers = {"Authorization": "Bearer limited-identity-001"}
            codes = [
                client.post("/api/v1/brief", json={"question": "q"}, headers=headers).status_code
                for _ in range(3)
            ]
        self.assertEqual(codes[:2], [200, 200])
        self.assertEqual(codes[2], 429)
        r = client.post("/api/v1/brief", json={"question": "q"}, headers=headers)
        self.assertEqual(r.json()["error"]["code"], "RATE_LIMITED")

    def test_access_logging(self) -> None:
        with api_client() as (client, app):
            install_fakes(app)
            with self.assertLogs("api", level="INFO") as captured:
                client.get("/api/v1/health", headers={"X-Request-ID": "rid-1"})
        text = "\n".join(captured.output)
        self.assertIn("route=/api/v1/health", text)
        self.assertIn("api_version=v1", text)
        self.assertIn("request_id=rid-1", text)
        self.assertNotIn(VALID_KEY, text)


class EndpointTests(unittest.TestCase):
    def test_brief_passthrough_and_validation(self) -> None:
        with api_client() as (client, app):
            install_fakes(app)
            ok = client.post("/api/v1/brief", json={"question": "NATO?", "max_docs": 2})
            bad = client.post("/api/v1/brief", json={"question": ""})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["documents_used"], ["nato"])
        # FakeBrief received stripped value path through service
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(bad.json()["error"]["code"], "INVALID_REQUEST")

    def test_analyze(self) -> None:
        with api_client() as (client, app):
            install_fakes(app)
            r = client.post("/api/v1/analyze", json={"question": "NATO?"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("critical_analysis", r.json())

    def test_compare(self) -> None:
        with api_client() as (client, app):
            install_fakes(app)
            r = client.post("/api/v1/compare", json={"question": "NATO?"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("comparison", r.json())

    def test_producer_update_job_lifecycle(self) -> None:
        with api_client() as (client, _):
            with mock.patch(
                "producer.cli.run", return_value="• nato: already current; no changes."
            ):  # offline
                r = client.post(
                    "/api/v1/producer/update", json={"concept_id": "nato", "dry_run": True}
                )
                self.assertEqual(r.status_code, 202)
                job_id = r.json()["job_id"]
                self.assertEqual(r.json()["status"], "pending")
                record = wait_for_job(client, job_id)
        self.assertEqual(record["status"], "succeeded")
        self.assertIn("already current", record["result"]["report"])
        self.assertIsNotNone(record["started_at"])
        self.assertIsNotNone(record["finished_at"])

    def test_producer_update_all_accepts_and_queues(self) -> None:
        with api_client() as (client, app):
            fake_jobs = FakeJobService()
            app.state.producer_jobs = fake_jobs
            r = client.post("/api/v1/producer/update-all", json={"dry_run": True})
        self.assertEqual(r.status_code, 202)
        self.assertEqual(r.json()["job_type"], "producer.update_all")

    def test_jobs_endpoints(self) -> None:
        with api_client() as (client, _):
            with mock.patch("producer.cli.run", return_value="ok"):
                job_id = client.post("/api/v1/producer/update", json={"concept_id": "nato"}).json()[
                    "job_id"
                ]
                wait_for_job(client, job_id)
                listing = client.get("/api/v1/jobs")
                missing = client.get("/api/v1/jobs/nope")
        self.assertEqual(listing.status_code, 200)
        self.assertTrue(any(j["job_id"] == job_id for j in listing.json()))
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["error"]["code"], "JOB_NOT_FOUND")

    def test_health_ready_version_metrics(self) -> None:
        with api_client(make_settings(git_sha="abc123")) as (client, _):
            self.assertEqual(client.get("/api/v1/health").json()["status"], "ok")
            ready = client.get("/api/v1/ready")
            version = client.get("/api/v1/version").json()
            metrics = client.get("/api/v1/metrics")
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["status"], "ready")
        self.assertTrue(ready.json()["checks"]["bundle_accessible"])
        self.assertIn("briefing", ready.json()["checks"]["consumers"])
        self.assertEqual(version["git_sha"], "abc123")
        self.assertEqual(version["bundle_version"], 1)
        self.assertEqual(version["app_version"], "test")
        self.assertIn("requests_total", metrics.text)

    def test_ready_degrades_when_consumer_misconfigured(self) -> None:
        with api_client() as (client, app):
            registry = app.state.registry
            broken = replace(registry.get("briefing"), client_error="GROQ_API_KEY is not set")
            registry._by_name["briefing"] = broken
            r = client.get("/api/v1/ready")
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["status"], "not_ready")
        self.assertFalse(r.json()["checks"]["consumers"]["briefing"]["client_ready"])


class ErrorMappingTests(unittest.TestCase):
    def _post_with_error(self, exc: Exception):
        class FailBrief:
            def brief(self, q, m, rid):
                raise exc

        with api_client() as (client, app):
            install_fakes(app)
            app.state.briefing_service = FailBrief()
            return client.post(
                "/api/v1/brief", json={"question": "q"}, headers={"Authorization": "Bearer err-id"}
            )

    def test_provider_timeout(self) -> None:
        from consumer_a.exceptions import TimeoutError as ATimeout

        r = self._post_with_error(ATimeout("slow"))
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (504, "UPSTREAM_TIMEOUT"))

    def test_provider_failure(self) -> None:
        from consumer_a.exceptions import LLMResponseError

        r = self._post_with_error(LLMResponseError("bad json"))
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (502, "UPSTREAM_LLM"))

    def test_malformed_bundle(self) -> None:
        from consumer_a.exceptions import DocumentReadError

        r = self._post_with_error(DocumentReadError("broken"))
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (503, "BUNDLE_UNAVAILABLE"))

    def test_filesystem_failure(self) -> None:
        from consumer_b.exceptions import FilesystemError

        r = self._post_with_error(FilesystemError("disk"))
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (503, "BUNDLE_UNAVAILABLE"))

    def test_internal_error(self) -> None:
        r = self._post_with_error(RuntimeError("boom"))
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (500, "INTERNAL"))
        self.assertIn("request_id", r.json()["error"])

    def test_failed_job_carries_mapped_code(self) -> None:
        from consumer_a.exceptions import LLMResponseError

        def boom():
            raise LLMResponseError("LLM exploded")

        with api_client() as (client, app):
            record = app.state.jobs.submit("producer.update", boom)
            time.sleep(0.3)
            finished = app.state.jobs.get(record.job_id)
        self.assertEqual(finished.status, "failed")
        self.assertEqual(finished.error["code"], "UPSTREAM_LLM")


class ComparisonServiceTests(unittest.TestCase):
    def _adapter(self, name, docs, sources, sleep=0.0, bundle_version=1):
        class FakeSvc:
            def answer(self, q, max_docs=None):
                if sleep:
                    time.sleep(sleep)
                return {"documents_used": docs}

        def payload(report):
            return {
                "documents_used": report["documents_used"],
                "sources": [{"source_url": u} for u in sources],
                "bundle_version": bundle_version,
            }

        return ConsumerAdapter(
            name=name,
            json_key=name,
            method_name="answer",
            service=FakeSvc(),
            route_hint=f"/{name}",
            provider="pv",
            model="m",
            payload=payload,
        )

    def test_deterministic_merge_metadata(self) -> None:
        registry = ConsumerRegistry(
            [
                self._adapter("briefing", ["nato", "ukraine"], ["https://a", "https://b"]),
                self._adapter("analysis", ["nato", "red-sea"], ["https://b", "https://c"]),
            ]
        )
        out = asyncio.run(ComparisonService(registry).compare("q?", None, "rid-9"))
        cmp = out["comparison"]
        self.assertEqual(cmp["shared_documents"], ["nato"])
        self.assertEqual(cmp["shared_sources"], ["https://b"])
        self.assertTrue(cmp["bundle_versions_agree"])
        self.assertEqual(cmp["bundle_versions"], {"briefing": 1, "analysis": 1})
        self.assertEqual(cmp["consumers"]["briefing"]["provider"], "pv")
        self.assertIn("briefing", cmp["durations_ms"])

    def test_parallel_execution(self) -> None:
        registry = ConsumerRegistry(
            [
                self._adapter("briefing", [], [], sleep=0.4),
                self._adapter("analysis", [], [], sleep=0.4),
            ]
        )
        started = time.perf_counter()
        asyncio.run(ComparisonService(registry).compare("q?", None, "rid-1"))
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 0.7)  # ~0.4s when parallel, ~0.8s when sequential

    def test_bundle_version_disagreement(self) -> None:
        registry = ConsumerRegistry(
            [
                self._adapter("briefing", [], [], bundle_version=1),
                self._adapter("analysis", [], [], bundle_version=2),
            ]
        )
        out = asyncio.run(ComparisonService(registry).compare("q?", None, "rid-2"))
        self.assertFalse(out["comparison"]["bundle_versions_agree"])


class JobManagerTests(unittest.TestCase):
    def test_state_transitions(self) -> None:
        manager = JobManager(retention=10, max_workers=1)
        gate = __import__("threading").Event()
        record = manager.submit("t", lambda: (gate.wait(2), {"ok": True})[1])
        time.sleep(0.1)
        self.assertIn(manager.get(record.job_id).status, ("pending", "running"))
        gate.set()
        deadline = time.time() + 2
        while manager.get(record.job_id).status != "succeeded" and time.time() < deadline:
            time.sleep(0.02)
        self.assertEqual(manager.get(record.job_id).status, "succeeded")
        manager.shutdown()

    def test_retention_pruning(self) -> None:
        manager = JobManager(retention=3, max_workers=2)
        ids = [manager.submit("t", lambda: {"x": 1}).job_id for _ in range(6)]
        deadline = time.time() + 3
        while (
            any(
                manager.get(i) is not None and manager.get(i).status in ("pending", "running")
                for i in ids
            )
            and time.time() < deadline
        ):
            time.sleep(0.05)
        time.sleep(0.1)
        self.assertLessEqual(len(manager.list(10)), 3)
        manager.shutdown()

    def test_newest_first_listing(self) -> None:
        manager = JobManager(retention=10, max_workers=1)
        first = manager.submit("first", lambda: {})
        second = manager.submit("second", lambda: {})
        time.sleep(0.3)
        self.assertEqual([j.job_id for j in manager.list()], [second.job_id, first.job_id])
        manager.shutdown()

    def test_validation_failure_job_payload_keeps_full_detail(self) -> None:
        """A failing producer job exposes every validator error + staged path."""
        from producer.exceptions import ValidationFailure
        from validator.models import ValidationError, ValidationResult

        def boom() -> dict:
            raise ValidationFailure(
                ValidationResult(
                    checked=3,
                    errors=[
                        ValidationError(
                            code="OKF011",
                            file="actors/nato.md",
                            line=42,
                            rule="Malformed source entry",
                            suggested_fix="Add `accessed` to the source.",
                        )
                    ],
                ),
                staged_bundle="/tmp/okf-stage-test/bundle",
            )

        manager = JobManager(retention=10, max_workers=1)
        record = manager.submit("producer.update", boom)
        deadline = time.time() + 3
        while manager.get(record.job_id).status != "failed" and time.time() < deadline:
            time.sleep(0.02)
        manager.shutdown()

        record = manager.get(record.job_id)
        assert record is not None and record.error is not None
        self.assertEqual(record.error["code"], "BUNDLE_VALIDATION_FAILED")
        self.assertEqual(record.error["staged_bundle"], "/tmp/okf-stage-test/bundle")
        errors = record.error["validation_errors"]
        self.assertEqual(len(errors), 1)
        self.assertEqual(
            errors[0],
            {
                "code": "OKF011",
                "file": "actors/nato.md",
                "line": 42,
                "message": "Malformed source entry",
                "suggestion": "Add `accessed` to the source.",
            },
        )

    def test_failure_job_without_details_shape_unchanged(self) -> None:
        """Plain failures still produce exactly {code, message}."""

        def boom() -> dict:
            raise ValueError("boom")  # unexpected: maps to INTERNAL, no details

        manager = JobManager(retention=10, max_workers=1)
        record = manager.submit("t", boom)
        deadline = time.time() + 3
        while manager.get(record.job_id).status != "failed" and time.time() < deadline:
            time.sleep(0.02)
        manager.shutdown()

        record = manager.get(record.job_id)
        assert record is not None and record.error is not None
        self.assertEqual(set(record.error.keys()), {"code", "message"})


class OpenAPITests(unittest.TestCase):
    def test_schema_completeness(self) -> None:
        with api_client() as (client, _):
            self.assertEqual(client.get("/docs").status_code, 200)
            spec = client.get("/openapi.json").json()

        required = [
            "/api/v1/brief",
            "/api/v1/analyze",
            "/api/v1/compare",
            "/api/v1/producer/update",
            "/api/v1/producer/update-all",
            "/api/v1/jobs",
            "/api/v1/jobs/{job_id}",
            "/api/v1/health",
            "/api/v1/ready",
            "/api/v1/version",
            "/api/v1/metrics",
        ]
        for path in required:
            self.assertIn(path, spec["paths"], path)
        for path, methods in spec["paths"].items():
            for method, op in methods.items():
                self.assertTrue(op.get("summary"), f"{method} {path} missing summary")
                self.assertTrue(op.get("description"), f"{method} {path} missing description")
                self.assertTrue(op.get("tags"), f"{method} {path} missing tags")

    def test_producer_job_response_models(self) -> None:
        with api_client() as (client, _):
            spec = client.get("/openapi.json").json()
        update = spec["paths"]["/api/v1/producer/update"]["post"]
        self.assertEqual(update["responses"]["202"]["description"], "Successful Response")
        self.assertIn("requestBody", update)


class LifecycleTests(unittest.TestCase):
    def test_client_reuse_and_graceful_shutdown(self) -> None:
        app = create_app(make_settings())
        with TestClient(app) as client:
            before = id(app.state.registry.get("briefing").client)
            client.get("/api/v1/health")
            after = id(app.state.registry.get("briefing").client)
        self.assertEqual(before, after)  # same pooled client
        self.assertTrue(app.state.jobs._executor._shutdown)  # pool stopped cleanly


class RegressionBundleTests(unittest.TestCase):
    def test_api_runs_leave_bundle_byte_identical(self) -> None:
        okf = Path(__file__).resolve().parent.parent / "okf"

        def snapshot():
            return {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(okf.rglob("*.md"))
            }

        before = snapshot()
        with api_client() as (client, app):
            install_fakes(app)
            client.post(
                "/api/v1/brief", json={"question": "q"}, headers={"Authorization": "Bearer snap-id"}
            )
            with mock.patch("producer.cli.run", return_value="ok"):
                client.post("/api/v1/producer/update", json={"concept_id": "nato"})
        after = snapshot()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
