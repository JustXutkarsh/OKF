"""Deterministic tests for the producer agent. No network access."""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from producer.cli import exit_code_for, main, run, run_all
from producer.config import load_config, load_registry
from producer.evidence import build_evidence
from producer.exceptions import (
    ConfigError,
    LLMResponseError,
    ProducerError,
    RegistryError,
    SearchError,
    ValidationFailure,
)
from producer.models import LLMDraft, ProducerConfig, SourceEntry
from producer.renderer import render_document
from producer.search import TavilySearch
from producer.summarizer import Summarizer, parse_draft
from producer.updater import build_update, compute_confidence, load_document
from validator.validator import validate_bundle

TODAY = date(2026, 8, 7)

NATO_DOC = """---
schema_version: 1
id: nato
type: concept
title: NATO
resource: actors
tags: [actor, alliance]
created_at: 2026-08-01
last_updated: 2026-08-06
confidence: verified
related: [ukraine-russia-frontline]
---

## Summary

NATO supports Ukraine and deters Russia.

## Developments

### 2026-08-06

Allies met in Brussels.

### 2026-08-01

Earlier entry.

## Key Actors

- NATO member states
- Ukraine

## Sources

- title: NATO news
  url: https://www.nato.int/news
  accessed: 2026-08-06
  note: NATO news page.
- title: AP NATO coverage
  url: https://apnews.com/nato
  accessed: 2026-08-05
  note: AP coverage.
"""

UKRAINE_DOC = (
    NATO_DOC.replace("id: nato", "id: ukraine-russia-frontline")
    .replace("title: NATO", "title: Ukraine-Russia Frontline")
    .replace("resource: actors", "resource: conflicts")
    .replace("related: [ukraine-russia-frontline]", "related: [nato]")
)

REGISTRY_YAML = """
- id: nato
  title: NATO
  resource: actors
  tags: [actor, alliance]
  related: [ukraine-russia-frontline]
  key_actors: [NATO member states, Ukraine]
  search_query: nato ukraine support
- id: ukraine-russia-frontline
  title: Ukraine-Russia Frontline
  resource: conflicts
  tags: [conflict]
  related: [nato]
  key_actors: [Ukraine, Russia]
  search_query: ukraine frontline
"""

REGISTRY_WITH_NEW_CONCEPT = REGISTRY_YAML + """
- id: opec-production-policy
  title: OPEC+ Production Policy
  resource: economics
  tags: [economics, energy]
  related: [nato]
  key_actors: [OPEC+ member states]
  search_query: opec production policy
"""

REGISTRY_WITH_BROKEN_LINK = REGISTRY_YAML + """
- id: broken-concept
  title: Broken Concept
  resource: economics
  tags: [economics]
  related: [missing-id]
  key_actors: [Nobody]
  search_query: anything
"""

RAW_RESULTS = [
    {
        "title": "Reuters NATO story",
        "url": "https://www.reuters.com/world/nato-story",
        "content": "Reuters reporting on NATO moves.",
        "published_date": "2026-08-06",
    },
    {
        "title": "BBC NATO story",
        "url": "https://www.bbc.com/news/nato-story",
        "content": "BBC reporting on NATO developments.",
        "published_date": "2026-08-05",
    },
]

DRAFT = LLMDraft(
    summary="NATO reinforces its eastern flank while allies expand support for Ukraine.",
    development="NATO announced additional eastern flank deployments this week.",
)


class FakeSearch:
    """Search client returning canned raw results."""

    def __init__(self, results: list) -> None:
        self.results = results
        self.calls = 0

    def search(self, query, lookback_days, max_results):
        self.calls += 1
        return self.results


class FailingSearch:
    """Search client that always fails like a network outage."""

    def __init__(self) -> None:
        self.calls = 0

    def search(self, query, lookback_days, max_results):
        self.calls += 1
        raise SearchError("Tavily search failed: connection timeout")


class FakeSummarizer:
    """Summarizer returning a fixed draft (or a canned error)."""

    def __init__(self, draft: LLMDraft = DRAFT, error: Exception | None = None) -> None:
        self.draft_result = draft
        self.error = error
        self.calls = 0

    def draft(self, system_prompt, user_prompt):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.draft_result


class project:
    """Temporary producer project: bundle + registry + config."""

    def __init__(self, docs: dict[str, str], registry_text: str = REGISTRY_YAML) -> None:
        self.docs = docs
        self.registry_text = registry_text
        self.tmp: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self) -> ProducerConfig:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for name, text in self.docs.items():
            path = root / "okf" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        registry_path = root / "config" / "tracked_concepts.yaml"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(self.registry_text, encoding="utf-8")
        return ProducerConfig(
            bundle_path=root / "okf",
            registry_path=registry_path,
            lookback_days=7,
            max_results=5,
            model="test-model",
        )

    def __exit__(self, *args) -> None:
        assert self.tmp is not None
        self.tmp.cleanup()


def two_doc_project(registry_text: str = REGISTRY_YAML):
    """Standard two-document project fixture."""

    return project(
        {"actors/nato.md": NATO_DOC, "conflicts/ukraine-russia-frontline.md": UKRAINE_DOC},
        registry_text,
    )


class UpdateFlowTests(unittest.TestCase):
    """Update and create flows through the full pipeline."""

    def test_existing_document_update(self) -> None:
        """Summary replaced, development prepended, metadata preserved."""

        with two_doc_project() as config:
            report = run(
                "nato",
                config=config,
                search_client=FakeSearch(RAW_RESULTS),
                summarizer=FakeSummarizer(),
                today=TODAY,
            )
            text = (config.bundle_path / "actors/nato.md").read_text(encoding="utf-8")

        self.assertIn("Update applied", report)
        doc = load_document(text)
        self.assertEqual(doc.summary, DRAFT.summary)
        self.assertEqual(
            [e.date for e in doc.developments], ["2026-08-07", "2026-08-06", "2026-08-01"]
        )
        self.assertEqual(doc.developments[0].text, DRAFT.development)
        self.assertEqual(doc.developments[1].text, "Allies met in Brussels.")
        self.assertEqual(doc.developments[2].text, "Earlier entry.")
        self.assertEqual(doc.last_updated, "2026-08-07")
        self.assertEqual(doc.created_at, "2026-08-01")
        self.assertEqual(doc.id, "nato")
        self.assertEqual(doc.title, "NATO")
        self.assertEqual(doc.tags, ["actor", "alliance"])
        self.assertEqual(doc.related, ["ukraine-russia-frontline"])
        self.assertEqual(doc.key_actors, ["NATO member states", "Ukraine"])
        self.assertEqual(len(doc.sources), 4)

    def test_new_document_creation(self) -> None:
        """A tracked concept without a file is created from the registry."""

        with two_doc_project(REGISTRY_WITH_NEW_CONCEPT) as config:
            report = run(
                "opec-production-policy",
                config=config,
                search_client=FakeSearch(RAW_RESULTS),
                summarizer=FakeSummarizer(),
                today=TODAY,
            )
            target = config.bundle_path / "economics/opec-production-policy.md"
            self.assertTrue(target.is_file())
            doc = load_document(target.read_text(encoding="utf-8"))
            result = validate_bundle(config.bundle_path)

        self.assertIn("Creation applied", report)
        self.assertTrue(result.ok)
        self.assertEqual(doc.created_at, "2026-08-07")
        self.assertEqual(doc.last_updated, "2026-08-07")
        self.assertEqual(doc.key_actors, ["OPEC+ member states"])
        self.assertEqual(doc.tags, ["economics", "energy"])
        self.assertEqual([e.date for e in doc.developments], ["2026-08-07"])

    def test_updated_bundle_passes_real_validator(self) -> None:
        """The written document is valid against the real validator."""

        with two_doc_project() as config:
            run(
                "nato",
                config=config,
                search_client=FakeSearch(RAW_RESULTS),
                summarizer=FakeSummarizer(),
                today=TODAY,
            )
            result = validate_bundle(config.bundle_path)
        self.assertTrue(result.ok, result.errors)

    def test_regression_unrelated_files_unchanged(self) -> None:
        """Updating one concept never modifies any other bundle document."""

        with two_doc_project() as config:
            other = config.bundle_path / "conflicts/ukraine-russia-frontline.md"
            before = other.read_bytes()
            run(
                "nato",
                config=config,
                search_client=FakeSearch(RAW_RESULTS),
                summarizer=FakeSummarizer(),
                today=TODAY,
            )
            after = other.read_bytes()
        self.assertEqual(before, after)


class NoOpAndCostTests(unittest.TestCase):
    """No-op paths and the zero-API-call same-day rule."""

    def test_same_day_rerun_makes_no_api_calls(self) -> None:
        """A document already current for today exits before any API spend."""

        with two_doc_project() as config:
            search = FakeSearch(RAW_RESULTS)
            summarizer = FakeSummarizer()
            report = run(
                "nato",
                config=config,
                search_client=search,
                summarizer=summarizer,
                today=date(2026, 8, 6),
            )
            text = (config.bundle_path / "actors/nato.md").read_text(encoding="utf-8")

        self.assertIn("already current", report)
        self.assertEqual(search.calls, 0)
        self.assertEqual(summarizer.calls, 0)
        self.assertEqual(text, NATO_DOC)

    def test_empty_search_result_is_noop(self) -> None:
        """No evidence means no LLM call and no write."""

        with two_doc_project() as config:
            summarizer = FakeSummarizer()
            report = run(
                "nato",
                config=config,
                search_client=FakeSearch([]),
                summarizer=summarizer,
                today=TODAY,
            )
            text = (config.bundle_path / "actors/nato.md").read_text(encoding="utf-8")

        self.assertIn("no evidence", report)
        self.assertEqual(summarizer.calls, 0)
        self.assertEqual(text, NATO_DOC)

    def test_dry_run_writes_nothing(self) -> None:
        """Dry run executes the full pipeline but never writes."""

        with two_doc_project() as config:
            report = run(
                "nato",
                config=config,
                search_client=FakeSearch(RAW_RESULTS),
                summarizer=FakeSummarizer(),
                dry_run=True,
                today=TODAY,
            )
            text = (config.bundle_path / "actors/nato.md").read_text(encoding="utf-8")

        self.assertIn("Dry run", report)
        self.assertIn("Validation: passed", report)
        self.assertEqual(text, NATO_DOC)


class FailureRollbackTests(unittest.TestCase):
    """Nothing is ever written when any pipeline stage fails."""

    def test_validator_failure_rollback(self) -> None:
        """Staged bundle failing validation is never written."""

        with two_doc_project(REGISTRY_WITH_BROKEN_LINK) as config:
            target = config.bundle_path / "economics/broken-concept.md"
            nato_before = (config.bundle_path / "actors/nato.md").read_bytes()
            with self.assertRaises(ValidationFailure) as ctx:
                run(
                    "broken-concept",
                    config=config,
                    search_client=FakeSearch(RAW_RESULTS),
                    summarizer=FakeSummarizer(),
                    today=TODAY,
                )
            nato_after = (config.bundle_path / "actors/nato.md").read_bytes()

        self.assertIn("OKF007", str(ctx.exception))
        self.assertFalse(target.exists())
        self.assertEqual(nato_before, nato_after)

    def test_atomic_write_failure_rollback(self) -> None:
        """A failing os.replace leaves the original document intact."""

        with two_doc_project() as config:
            target = config.bundle_path / "actors/nato.md"
            before = target.read_text(encoding="utf-8")
            with mock.patch("producer.writer.os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    run(
                        "nato",
                        config=config,
                        search_client=FakeSearch(RAW_RESULTS),
                        summarizer=FakeSummarizer(),
                        today=TODAY,
                    )
            after = target.read_text(encoding="utf-8")
            leftovers = list((config.bundle_path / "actors").glob("*.tmp"))

        self.assertEqual(before, after)
        self.assertEqual(leftovers, [])

    def test_failed_search_propagates(self) -> None:
        """A search failure aborts before any LLM call and writes nothing."""

        with two_doc_project() as config:
            summarizer = FakeSummarizer()
            with self.assertRaises(SearchError):
                run(
                    "nato",
                    config=config,
                    search_client=FailingSearch(),
                    summarizer=summarizer,
                    today=TODAY,
                )
            text = (config.bundle_path / "actors/nato.md").read_text(encoding="utf-8")

        self.assertEqual(summarizer.calls, 0)
        self.assertEqual(text, NATO_DOC)

    def test_malformed_llm_response_aborts(self) -> None:
        """An LLM contract failure aborts the pipeline without writing."""

        with two_doc_project() as config:
            summarizer = FakeSummarizer(error=LLMResponseError("Malformed LLM response: not JSON"))
            with self.assertRaises(LLMResponseError):
                run(
                    "nato",
                    config=config,
                    search_client=FakeSearch(RAW_RESULTS),
                    summarizer=summarizer,
                    today=TODAY,
                )
            text = (config.bundle_path / "actors/nato.md").read_text(encoding="utf-8")

        self.assertEqual(text, NATO_DOC)


class RenderingTests(unittest.TestCase):
    """Serialization invariance and determinism."""

    def test_round_trip_invariance_on_fixtures(self) -> None:
        """Parse + render reproduces the input document byte-for-byte."""

        for text in (NATO_DOC, UKRAINE_DOC):
            self.assertEqual(render_document(load_document(text)), text)

    def test_round_trip_invariance_on_real_bundle(self) -> None:
        """Every document in the real bundle round-trips byte-for-byte."""

        bundle = Path(__file__).resolve().parent.parent / "okf"
        for path in sorted(bundle.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertEqual(render_document(load_document(text)), text, str(path))

    def test_rendering_is_deterministic(self) -> None:
        """Rendering the same model twice produces identical output."""

        doc = load_document(NATO_DOC)
        self.assertEqual(render_document(doc), render_document(doc))

    def test_duplicate_url_removal(self) -> None:
        """Evidence URLs are deduped against existing sources and each other."""

        dupes = [
            {"title": "Dup of existing", "url": "https://www.nato.int/news/", "content": "x"},
            {"title": "New story", "url": "https://apnews.com/nato-new", "content": "y"},
            {"title": "Same new story", "url": "http://APNEWS.com/nato-new/", "content": "z"},
        ]
        doc = load_document(NATO_DOC)
        with two_doc_project() as config:
            registry = load_registry(config.registry_path)
            updated = build_update(
                doc, registry["nato"], DRAFT, build_evidence(dupes, 5), today="2026-08-07"
            )

        urls = [s.url for s in updated.sources]
        self.assertEqual(len(updated.sources), 3)  # 2 existing + 1 genuinely new
        self.assertEqual(urls.count("https://apnews.com/nato-new"), 1)


class ContractTests(unittest.TestCase):
    """LLM contract, provider responses, and config errors."""

    def test_parse_draft_rejects_non_json(self) -> None:
        with self.assertRaises(LLMResponseError):
            parse_draft("this is not json {")

    def test_parse_draft_rejects_missing_fields(self) -> None:
        with self.assertRaises(LLMResponseError):
            parse_draft('{"summary": "only one field"}')

    def test_parse_draft_rejects_urls_in_output(self) -> None:
        with self.assertRaises(LLMResponseError):
            parse_draft('{"summary": "see https://evil.example", "development": "x"}')

    def test_malformed_tavily_response(self) -> None:
        """A response without a results list is a SearchError, not a crash."""

        class StubClient:
            def search(self, **kwargs):
                return "<html>gateway error</html>"

        search = TavilySearch.__new__(TavilySearch)
        search._client = StubClient()
        with self.assertRaises(SearchError):
            search.search("query", 7, 5)

    def test_malformed_tavily_items_are_dropped(self) -> None:
        """Items missing url/title are dropped; a fully bad batch is empty."""

        self.assertEqual(build_evidence([{"url": "no title"}, "junk", None], 5), [])

    def test_unknown_concept(self) -> None:
        with two_doc_project() as config:
            with self.assertRaises(RegistryError):
                run(
                    "ghost-concept",
                    config=config,
                    search_client=FakeSearch([]),
                    summarizer=FakeSummarizer(),
                )

    def test_missing_tavily_key(self) -> None:
        with two_doc_project() as config:
            with self.assertRaisesRegex(ConfigError, "TAVILY_API_KEY"):
                TavilySearch(config)

    def test_missing_groq_key(self) -> None:
        with two_doc_project() as config:
            with self.assertRaisesRegex(ConfigError, "GROQ_API_KEY"):
                Summarizer(config)

    def test_missing_openai_key_for_openai_provider(self) -> None:
        """Provider openai requires OPENAI_API_KEY, not GROQ_API_KEY."""

        with two_doc_project() as config:
            openai_config = config.model_copy(
                update={"llm_provider": "openai", "openai_api_key": None}
            )
            with self.assertRaisesRegex(ConfigError, "OPENAI_API_KEY"):
                Summarizer(openai_config)


class ConfidenceTests(unittest.TestCase):
    """Deterministic confidence tiers from independent domains."""

    def _sources(self, urls: list[str]) -> list[SourceEntry]:
        return [SourceEntry(title="t", url=u, accessed="2026-08-07", note="n") for u in urls]

    def test_verified_tier(self) -> None:
        urls = ["https://a.com/1", "https://b.org/2", "https://c.net/3"]
        self.assertEqual(compute_confidence(self._sources(urls)), "verified")

    def test_mixed_tier(self) -> None:
        urls = ["https://a.com/1", "https://b.org/2"]
        self.assertEqual(compute_confidence(self._sources(urls)), "mixed")

    def test_unverified_tier(self) -> None:
        urls = ["https://a.com/1", "https://a.com/2", "https://a.com/3"]
        self.assertEqual(compute_confidence(self._sources(urls)), "unverified")


class ConfigurationTests(unittest.TestCase):
    """Centralized configuration: env vars, .env (dev only), defaults."""

    def test_env_overrides_paths_and_settings(self) -> None:
        env = {
            "OKF_BUNDLE_PATH": "/tmp/custom-bundle",
            "OKF_REGISTRY_PATH": "/tmp/custom-registry.yaml",
            "OKF_PRODUCER_MODEL": "custom-model",
            "OKF_PRODUCER_LLM_PROVIDER": "openai",
            "OKF_LOOKBACK_DAYS": "3",
            "OKF_MAX_RESULTS": "9",
            "OKF_REQUEST_TIMEOUT": "10",
            "OKF_LOG_LEVEL": "DEBUG",
            "TAVILY_API_KEY": "t-key",
            "GROQ_API_KEY": "g-key",
            "OPENAI_API_KEY": "o-key",
        }
        config = load_config(env=env, dotenv_path=None)
        self.assertEqual(str(config.bundle_path), "/tmp/custom-bundle")
        self.assertEqual(str(config.registry_path), "/tmp/custom-registry.yaml")
        self.assertEqual(config.model, "custom-model")
        self.assertEqual(config.llm_provider, "openai")
        self.assertEqual(config.lookback_days, 3)
        self.assertEqual(config.max_results, 9)
        self.assertEqual(config.request_timeout, 10)
        self.assertEqual(config.log_level, "DEBUG")
        self.assertEqual(config.tavily_api_key, "t-key")
        self.assertEqual(config.groq_api_key, "g-key")
        self.assertEqual(config.openai_api_key, "o-key")

    def test_defaults_without_env(self) -> None:
        config = load_config(env={}, dotenv_path=None)
        self.assertEqual(config.model, "llama-3.3-70b-versatile")
        self.assertEqual(config.llm_provider, "groq")
        self.assertEqual(config.lookback_days, 7)
        self.assertEqual(config.max_results, 5)
        self.assertTrue(str(config.bundle_path).endswith("okf"))

    def test_unsupported_llm_provider_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigError, "Unsupported LLM provider"):
            load_config(env={"OKF_PRODUCER_LLM_PROVIDER": "anthropic"}, dotenv_path=None)

    def test_invalid_int_setting_is_config_error(self) -> None:
        with self.assertRaisesRegex(ConfigError, "OKF_LOOKBACK_DAYS"):
            load_config(env={"OKF_LOOKBACK_DAYS": "seven"}, dotenv_path=None)

    def test_dotenv_loaded_for_development(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dotenv = Path(tmp) / ".env"
            dotenv.write_text(
                '# dev keys\nTAVILY_API_KEY=from-file\nexport GROQ_API_KEY="quoted-value"\n',
                encoding="utf-8",
            )
            config = load_config(env={}, dotenv_path=dotenv)
        self.assertEqual(config.tavily_api_key, "from-file")
        self.assertEqual(config.groq_api_key, "quoted-value")

    def test_dotenv_never_overrides_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dotenv = Path(tmp) / ".env"
            dotenv.write_text("TAVILY_API_KEY=from-file\n", encoding="utf-8")
            config = load_config(env={"TAVILY_API_KEY": "from-env"}, dotenv_path=dotenv)
        self.assertEqual(config.tavily_api_key, "from-env")

    def test_dotenv_inline_comments_stripped(self) -> None:
        """Inline comments after unquoted values are ignored, like .env.example."""

        with tempfile.TemporaryDirectory() as tmp:
            dotenv = Path(tmp) / ".env"
            dotenv.write_text(
                "OKF_PRODUCER_MODEL=llama-3.3-70b-versatile  # producer model\n"
                "TAVILY_API_KEY=abc#not-a-comment\n",
                encoding="utf-8",
            )
            config = load_config(env={}, dotenv_path=dotenv)
        self.assertEqual(config.model, "llama-3.3-70b-versatile")
        self.assertEqual(config.tavily_api_key, "abc#not-a-comment")

    def test_malformed_dotenv_line_is_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dotenv = Path(tmp) / ".env"
            dotenv.write_text("TAVILY_API_KEY=ok\nTHIS LINE IS BROKEN\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(env={}, dotenv_path=dotenv)


class ObservabilityTests(unittest.TestCase):
    """Structured logging: concept id, stage durations, no secrets."""

    def test_structured_run_logging(self) -> None:
        with two_doc_project() as config:
            with self.assertLogs("producer", level="INFO") as captured:
                run(
                    "nato",
                    config=config,
                    search_client=FakeSearch(RAW_RESULTS),
                    summarizer=FakeSummarizer(),
                    today=TODAY,
                )
        text = "\n".join(captured.output)
        for token in (
            "run.start",
            "concept=nato",
            "stage=search",
            "duration_ms=",
            "stage=llm",
            "stage=validate",
            "stage=write",
            "run.complete",
            "total_ms=",
        ):
            self.assertIn(token, text)
        self.assertNotIn("api_key", text.lower())


class ExitCodeTests(unittest.TestCase):
    """Documented exit-code taxonomy."""

    def test_exit_code_mapping(self) -> None:
        from validator.models import ValidationError, ValidationResult

        failure = ValidationFailure(
            ValidationResult(
                checked=1,
                errors=[ValidationError(code="OKF007", file="x.md", rule="r", suggested_fix="f")],
            )
        )
        self.assertEqual(exit_code_for(failure), 5)
        self.assertEqual(exit_code_for(ConfigError("x")), 3)
        self.assertEqual(exit_code_for(RegistryError("x")), 3)
        self.assertEqual(exit_code_for(SearchError("x")), 4)
        self.assertEqual(exit_code_for(LLMResponseError("x")), 4)
        self.assertEqual(exit_code_for(OSError("x")), 6)
        self.assertEqual(exit_code_for(ProducerError("x")), 1)

    def test_main_missing_key_exits_config(self) -> None:
        import producer.config as producer_config

        real_load_config = producer_config.load_config
        with two_doc_project() as config:
            # Make the doc never-current so the pipeline reaches the key check.
            target = config.bundle_path / "actors/nato.md"
            target.write_text(
                target.read_text(encoding="utf-8").replace("### 2026-08-06", "### 2000-01-30"),
                encoding="utf-8",
            )
            env = {
                "OKF_BUNDLE_PATH": str(config.bundle_path),
                "OKF_REGISTRY_PATH": str(config.registry_path),
            }
            # Pin the .env fallback off: the machine's real .env (if present)
            # must not leak keys into this isolation test.
            with mock.patch.dict(os.environ, env, clear=True):
                with mock.patch(
                    "producer.cli.load_config",
                    side_effect=lambda: real_load_config(dotenv_path=None),
                ):
                    with contextlib.redirect_stdout(io.StringIO()):
                        code = main(["update", "nato"])
        self.assertEqual(code, 3)

    def test_main_requires_concept_or_all(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stderr(io.StringIO()):
                main(["update"])
        self.assertEqual(ctx.exception.code, 2)


class UpdateAllTests(unittest.TestCase):
    """--all batch behavior for schedulers."""

    def test_update_all_processes_each_concept(self) -> None:
        with two_doc_project() as config:
            reports, code = run_all(
                config=config,
                search_client=FakeSearch(RAW_RESULTS),
                summarizer=FakeSummarizer(),
                today=TODAY,
            )
        self.assertEqual(code, 0)
        self.assertTrue(any("Update applied — nato" in line for line in reports))
        self.assertTrue(any("ukraine-russia-frontline" in line for line in reports))

    def test_update_all_continues_after_failure(self) -> None:
        with two_doc_project(REGISTRY_WITH_BROKEN_LINK) as config:
            reports, code = run_all(
                config=config,
                search_client=FakeSearch(RAW_RESULTS),
                summarizer=FakeSummarizer(),
                today=TODAY,
            )
        self.assertEqual(code, 5)
        self.assertTrue(any("✖ broken-concept" in line for line in reports))
        self.assertTrue(any("Update applied — nato" in line for line in reports))
        self.assertFalse((config.bundle_path / "economics/broken-concept.md").exists())


class ValidationDebuggingTests(unittest.TestCase):
    """Observability regression: full validation detail survives to the caller."""

    def test_failure_carries_full_validation_errors(self) -> None:
        """ValidationFailure.validation_errors has code/file/line/message/suggestion."""

        with two_doc_project(REGISTRY_WITH_BROKEN_LINK) as config:
            with self.assertRaises(ValidationFailure) as ctx:
                run(
                    "broken-concept",
                    config=config,
                    search_client=FakeSearch(RAW_RESULTS),
                    summarizer=FakeSummarizer(),
                    today=TODAY,
                )

        errors = ctx.exception.validation_errors
        self.assertTrue(errors)
        first = errors[0]
        self.assertEqual(set(first), {"code", "file", "line", "message", "suggestion"})
        self.assertEqual(first["code"], "OKF007")
        self.assertTrue(first["file"])
        self.assertTrue(first["message"])
        self.assertTrue(first["suggestion"])
        self.assertIn("OKF007", str(ctx.exception))
        self.assertIsNone(ctx.exception.staged_bundle)

    def test_errors_logged_before_failure(self) -> None:
        """Every validation error is logged individually before the failure."""

        with two_doc_project(REGISTRY_WITH_BROKEN_LINK) as config:
            with self.assertLogs("producer", level="INFO") as logs:
                try:
                    run(
                        "broken-concept",
                        config=config,
                        search_client=FakeSearch(RAW_RESULTS),
                        summarizer=FakeSummarizer(),
                        today=TODAY,
                    )
                except ValidationFailure:
                    pass

        lines = "\n".join(logs.output)
        self.assertIn("validation.error", lines)
        self.assertIn("code=OKF007", lines)
        self.assertIn("file=economics/broken-concept.md", lines)

    def test_keep_failed_stage_preserves_bundle(self) -> None:
        """OKF_KEEP_FAILED_STAGE=true keeps the staged bundle and returns its path."""

        from producer.validator_adapter import validate_staged

        with two_doc_project() as config:
            with mock.patch.dict(os.environ, {"OKF_KEEP_FAILED_STAGE": "true"}):
                with self.assertLogs("producer", level="INFO") as logs:
                    result, staged_path = validate_staged(
                        config.bundle_path, "actors/nato.md", "not valid yaml"
                    )

        self.assertFalse(result.ok)
        self.assertIsNotNone(staged_path)
        assert staged_path is not None
        kept = Path(staged_path)
        try:
            self.assertTrue(kept.is_dir())
            self.assertEqual(
                (kept / "actors/nato.md").read_text(encoding="utf-8"), "not valid yaml"
            )
            self.assertTrue((kept / "conflicts/ukraine-russia-frontline.md").exists())
            self.assertIn(str(kept), "\n".join(logs.output))
        finally:
            import shutil

            shutil.rmtree(kept.parent, ignore_errors=True)

    def test_without_debug_env_staged_bundle_is_removed(self) -> None:
        """Default (unset) keeps nothing on disk and returns no path."""

        from producer.validator_adapter import validate_staged

        with two_doc_project() as config:
            env = {key: value for key, value in os.environ.items()}
            env.pop("OKF_KEEP_FAILED_STAGE", None)
            with mock.patch.dict(os.environ, env, clear=True):
                result, staged_path = validate_staged(
                    config.bundle_path, "actors/nato.md", "not valid yaml"
                )

        self.assertFalse(result.ok)
        self.assertIsNone(staged_path)


class ApiValidationDetailTests(unittest.TestCase):
    """API surface: job/HTTP mapping keeps the full diagnostics."""

    def test_map_component_error_includes_validation_details(self) -> None:
        from api.core.errors import map_component_error

        failure = ValidationFailure(
            __import__("validator.models", fromlist=["ValidationResult"]).ValidationResult(
                checked=2,
                errors=[
                    __import__("validator.models", fromlist=["ValidationError"]).ValidationError(
                        code="OKF011",
                        file="actors/nato.md",
                        line=42,
                        rule="Malformed source entry",
                        suggested_fix="Add `accessed` to the source.",
                    )
                ],
            ),
            staged_bundle="/tmp/okf-stage-abc/nukes",
        )
        mapped = map_component_error(failure)
        self.assertEqual(mapped.status, 409)
        self.assertEqual(mapped.code, "BUNDLE_VALIDATION_FAILED")
        assert mapped.details is not None
        errors = mapped.details["validation_errors"]
        assert isinstance(errors, list)
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
        self.assertEqual(mapped.details["staged_bundle"], "/tmp/okf-stage-abc/nukes")

    def test_map_component_error_without_staged_bundle_omits_key(self) -> None:
        from api.core.errors import map_component_error

        failure = ValidationFailure(
            __import__("validator.models", fromlist=["ValidationResult"]).ValidationResult(
                checked=1,
                errors=[
                    __import__("validator.models", fromlist=["ValidationError"]).ValidationError(
                        code="OKF007",
                        file="x.md",
                        rule="Broken link",
                        suggested_fix="Fix the link.",
                    )
                ],
            )
        )
        mapped = map_component_error(failure)
        assert mapped.details is not None
        self.assertNotIn("staged_bundle", mapped.details)
        self.assertEqual(mapped.details["validation_errors"][0]["code"], "OKF007")


if __name__ == "__main__":
    unittest.main()
