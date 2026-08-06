"""Deterministic offline tests for Consumer A. No network access."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from consumer_a import NOT_COVERED_SENTENCE
from consumer_a.cli import exit_code_for, main
from consumer_a.config import load_config
from consumer_a.exceptions import (
    ConfigError,
    DocumentReadError,
    FilesystemError,
    LLMResponseError,
    RetrievalError,
)
from consumer_a.exceptions import TimeoutError as ProviderTimeoutError
from consumer_a.llm import ChatClient, parse_briefing
from consumer_a.models import (
    AnswerReport,
    Briefing,
    CatalogEntry,
    ConsumerConfig,
    RetrievalDiagnostics,
)
from consumer_a.renderer import render_json, render_text
from consumer_a.retriever import (
    id_score,
    phrase_bonus,
    resource_score,
    select,
    tag_score,
    title_score,
    total_score,
)
from consumer_a.service import ConsumerService

FIXED_CLOCK = lambda: datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc)

NATO_DOC = """---
schema_version: 1
id: nato
type: concept
title: NATO
resource: actors
tags: [actor, alliance, europe]
created_at: 2026-08-01
last_updated: 2026-08-06
confidence: verified
related: [ukraine-russia-frontline]
---

## Summary

NATO is reinforcing its eastern flank.

## Developments

### 2026-08-06

Allies pledged air defense systems.

## Key Actors

- NATO member states
- Ukraine

## Sources

- title: NATO topic page
  url: https://www.nato.int/topic
  accessed: 2026-08-06
  note: Topic page.
"""

UKRAINE_DOC = NATO_DOC.replace("id: nato", "id: ukraine-russia-frontline").replace(
    "title: NATO", "title: Ukraine-Russia Frontline"
).replace("resource: actors", "resource: conflicts").replace(
    "tags: [actor, alliance, europe]", "tags: [conflict, ukraine, russia]"
).replace("confidence: verified", "confidence: mixed").replace(
    "related: [ukraine-russia-frontline]", "related: [nato]"
)

TARIFF_DOC = NATO_DOC.replace("id: nato", "id: us-china-tariffs").replace(
    "title: NATO", "title: US-China Tariffs"
).replace("resource: actors", "resource: economics").replace(
    "tags: [actor, alliance, europe]", "tags: [economics, us-china, tariffs]"
).replace("confidence: verified", "confidence: emerging").replace(
    "related: [ukraine-russia-frontline]", "related: []"
)

THREE_DOC_BUNDLE = {
    "actors/nato.md": NATO_DOC,
    "conflicts/ukraine-russia-frontline.md": UKRAINE_DOC,
    "economics/us-china-tariffs.md": TARIFF_DOC,
}

COVERED_JSON = json.dumps(
    {
        "current_situation": "NATO maintains an enhanced eastern-flank posture.",
        "key_developments": ["Allies pledged air defense systems."],
        "key_actors": ["NATO member states", "Ukraine"],
        "reasoning": "Grounded in the NATO concept document.",
    }
)

UNCOVERED_JSON = json.dumps(
    {
        "current_situation": NOT_COVERED_SENTENCE,
        "key_developments": [],
        "key_actors": [],
        "reasoning": "",
    }
)


class FakeChat:
    """Fake LLM client: canned text or canned error; counts calls."""

    def __init__(self, text: str = COVERED_JSON, error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls = 0

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.text


class bundle:
    """Temporary bundle directory fixture."""

    def __init__(self, files: dict[str, str]) -> None:
        self.files = files
        self.tmp: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self) -> Path:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for name, text in self.files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return root

    def __exit__(self, *args) -> None:
        assert self.tmp is not None
        self.tmp.cleanup()


def make_service(bundle_path: Path, llm: object | None = None) -> ConsumerService:
    """Service with fixed config, injected LLM, and a frozen clock."""

    config = ConsumerConfig(bundle_path=bundle_path)
    return ConsumerService(config, llm_client=llm or FakeChat(), clock=FIXED_CLOCK)


def snapshot_tree(root: Path) -> dict[str, str]:
    """sha256 of every file, for write-freedom assertions."""

    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def catalog_entry(
    id: str, title: str, resource: str = "conflicts", tags: list[str] | None = None
) -> CatalogEntry:
    return CatalogEntry(id=id, title=title, resource=resource, tags=tags or [], relative_path=f"{resource}/{id}.md")


class RetrievalTests(unittest.TestCase):
    """Deterministic scoring, ranking stability, diagnostics."""

    def test_signal_scores_are_exact(self) -> None:
        """Each signal function contributes exactly its weighted share."""

        entry = catalog_entry(
            "red-sea-shipping-disruption",
            "Red Sea Shipping Disruption",
            tags=["maritime-security", "trade"],
        )
        question = "Red Sea shipping"
        tokens = ["red", "sea", "shipping"]
        self.assertEqual(title_score(tokens, entry), 12)   # 3 hits x 4
        self.assertEqual(tag_score(tokens, entry), 0)
        self.assertEqual(id_score(tokens, entry), 6)       # 3 hits x 2
        self.assertEqual(resource_score(tokens, entry), 0)
        self.assertEqual(phrase_bonus(question, entry), 5)
        self.assertEqual(total_score(question, entry), 23)

    def test_deterministic_ranking(self) -> None:
        catalog = [
            catalog_entry("us-china-tariffs", "US-China Tariffs", "economics", ["tariffs"]),
            catalog_entry("nato", "NATO", "actors", ["alliance"]),
            catalog_entry(
                "us-export-controls-semiconductors",
                "US Semiconductor Export Controls",
                "policy",
                ["us-china", "export-controls"],
            ),
        ]
        result = select(catalog, "US-China tariffs and export controls", 3)
        self.assertEqual(
            [row.document_id for row in result.ranking],
            ["us-export-controls-semiconductors", "us-china-tariffs"],
        )
        for row in result.ranking:
            self.assertEqual(
                row.title_score + row.tag_score + row.id_score + row.resource_score + row.phrase_bonus,
                row.total_score,
            )

    def test_identical_ranking_across_repeated_runs(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            first = make_service(root).answer("tariffs")
            second = make_service(root).answer("tariffs")
        self.assertEqual(render_json(first), render_json(second))

    def test_body_reads_only_for_selected_documents(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            service = make_service(root)
            with mock.patch(
                "consumer_a.service.read_documents", side_effect=None
            ) as read_spy:
                read_spy.side_effect = lambda path, entries: __import__(
                    "consumer_a.reader", fromlist=["read_documents"]
                ).read_documents(path, entries)
                report = service.answer("NATO alliance")
            calls = [call.args[1] for call in read_spy.call_args_list]
        self.assertEqual(len(calls), 1)
        self.assertEqual([entry.id for entry in calls[0]], report.documents_used)
        self.assertNotIn("us-china-tariffs", [entry.id for entry in calls[0]])

    def test_retrieval_diagnostics_correctness(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            report = make_service(root).answer("NATO alliance")
        self.assertEqual(report.retrieval.candidate_count, 3)
        self.assertEqual(report.retrieval.selected_count, len(report.documents_used))
        self.assertEqual(report.retrieval.selected_documents, report.documents_used)
        self.assertGreaterEqual(report.retrieval.retrieval_time_ms, 0)
        totals = [row.total_score for row in report.ranking]
        self.assertEqual(totals, sorted(totals, reverse=True))


class LLMContractTests(unittest.TestCase):
    """parse_briefing strictness and client error mapping."""

    def test_valid_response(self) -> None:
        briefing = parse_briefing(COVERED_JSON)
        self.assertEqual(briefing.current_situation, "NATO maintains an enhanced eastern-flank posture.")
        self.assertEqual(briefing.reasoning, "Grounded in the NATO concept document.")

    def test_malformed_json(self) -> None:
        with self.assertRaises(LLMResponseError):
            parse_briefing("not json {")

    def test_code_fences_rejected(self) -> None:
        with self.assertRaisesRegex(LLMResponseError, "code fence"):
            parse_briefing(f"```json\n{COVERED_JSON}\n```")

    def test_unexpected_fields_rejected(self) -> None:
        payload = json.loads(COVERED_JSON)
        payload["sources"] = ["https://invented.example"]
        with self.assertRaises(LLMResponseError):
            parse_briefing(json.dumps(payload))

    def test_urls_rejected(self) -> None:
        for url in ("https://x.example", "http://x.example", "www.x.example"):
            payload = json.loads(COVERED_JSON)
            payload["current_situation"] = f"see {url}"
            with self.assertRaises(LLMResponseError):
                parse_briefing(json.dumps(payload))

    def test_citations_rejected(self) -> None:
        payload = json.loads(COVERED_JSON)
        payload["key_developments"] = ["Allies acted [1]."]
        with self.assertRaisesRegex(LLMResponseError, "citation"):
            parse_briefing(json.dumps(payload))

    def test_yaml_and_headings_rejected(self) -> None:
        for bad in ("line --- break", "# Heading"):
            payload = json.loads(COVERED_JSON)
            payload["reasoning"] = bad
            with self.assertRaises(LLMResponseError):
                parse_briefing(json.dumps(payload))

    def test_timeout_maps_to_timeout_error(self) -> None:
        client = ChatClient.__new__(ChatClient)
        client._model = "test-model"

        class StubInner:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("request timed out after 30s")

            chat = None

        stub = type("Stub", (), {"chat": type("C", (), {"completions": StubInner.completions})()})()
        client._client = stub
        with self.assertRaises(ProviderTimeoutError):
            client.chat("s", "u")

    def test_authentication_failure_is_clear(self) -> None:
        client = ChatClient.__new__(ChatClient)
        client._model = "test-model"
        client._key_env = "GROQ_API_KEY"

        class Completions:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("401 Unauthorized: invalid api key")

        client._client = type("Stub", (), {"chat": type("C", (), {"completions": Completions})()})()
        with self.assertRaisesRegex(LLMResponseError, "authentication failed"):
            client.chat("s", "u")

    def test_missing_key_names_provider_key_env(self) -> None:
        with self.assertRaisesRegex(ConfigError, "GROQ_API_KEY"):
            ChatClient(ConsumerConfig(bundle_path=Path("."), provider="groq"))
        with self.assertRaisesRegex(ConfigError, "OPENAI_API_KEY"):
            ChatClient(ConsumerConfig(bundle_path=Path("."), provider="openai"))

    def test_json_schema_validation_errors(self) -> None:
        for broken in (
            '{"current_situation": "s"}',                      # missing reasoning
            '{"current_situation": "", "reasoning": ""}',     # empty situation
            '[1, 2]',                                          # not an object
        ):
            with self.assertRaises(LLMResponseError):
                parse_briefing(broken)


class ServiceTests(unittest.TestCase):
    """End-to-end orchestration through ConsumerService.answer."""

    def test_covered_question(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            report = make_service(root).answer("What is NATO doing?")
        self.assertTrue(report.covered)
        self.assertEqual(report.documents_used, ["nato"])
        self.assertEqual(report.generated_at, "2026-08-06T12:00:00+00:00")
        self.assertTrue(report.evidence)
        sections = {e.section for e in report.evidence}
        self.assertEqual(sections, {"Summary", "Developments", "Key Actors"})
        self.assertEqual(report.evidence[0].confidence, "verified")
        self.assertTrue(report.sources)
        self.assertEqual(report.sources[0].accessed_date, "2026-08-06")
        self.assertEqual(report.sources[0].document_id, "nato")

    def test_retrieval_uncovered_makes_zero_llm_calls(self) -> None:
        fake = FakeChat()
        with bundle(THREE_DOC_BUNDLE) as root:
            report = make_service(root, fake).answer("What is the capital of France?")
        self.assertEqual(fake.calls, 0)
        self.assertFalse(report.covered)
        self.assertEqual(report.answer.current_situation, NOT_COVERED_SENTENCE)
        self.assertEqual(report.documents_used, [])
        self.assertEqual(report.evidence, [])
        self.assertEqual(report.sources, [])

    def test_llm_declared_not_covered(self) -> None:
        fake = FakeChat(UNCOVERED_JSON)
        with bundle(THREE_DOC_BUNDLE) as root:
            report = make_service(root, fake).answer("What is NATO doing?")
        self.assertEqual(fake.calls, 1)
        self.assertFalse(report.covered)
        self.assertEqual(report.answer.current_situation, NOT_COVERED_SENTENCE)
        self.assertEqual(report.documents_used, ["nato"])
        self.assertTrue(report.sources)

    def test_malformed_bundle_no_frontmatter(self) -> None:
        with bundle({"actors/nato.md": "## Just prose, no frontmatter\n"}) as root:
            with self.assertRaises(DocumentReadError):
                make_service(root).answer("NATO")

    def test_duplicate_ids_rejected(self) -> None:
        with bundle({"actors/nato.md": NATO_DOC, "conflicts/nato-copy.md": NATO_DOC}) as root:
            with self.assertRaisesRegex(DocumentReadError, "duplicate"):
                make_service(root).answer("NATO")

    def test_invalid_yaml_rejected(self) -> None:
        broken = NATO_DOC.replace("tags: [actor, alliance, europe]", "tags: [actor, alliance")
        with bundle({"actors/nato.md": broken}) as root:
            with self.assertRaisesRegex(DocumentReadError, "YAML"):
                make_service(root).answer("NATO")

    def test_filesystem_failure(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            with mock.patch.object(Path, "read_text", side_effect=OSError("disk gone")):
                with self.assertRaises(FilesystemError):
                    make_service(root).answer("NATO alliance")

    def test_empty_question_rejected(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            with self.assertRaises(RetrievalError):
                make_service(root).answer("   ")

    def test_llm_never_receives_sources_or_ids(self) -> None:
        captured: list[str] = []

        class CapturingChat(FakeChat):
            def chat(self, system_prompt, user_prompt):
                captured.append(user_prompt)
                return super().chat(system_prompt, user_prompt)

        with bundle(THREE_DOC_BUNDLE) as root:
            make_service(root, CapturingChat()).answer("NATO alliance")
        prompt = captured[0]
        self.assertNotIn("https://", prompt)
        self.assertNotIn(".md", prompt)
        self.assertNotIn("Sources:", prompt)


class RendererTests(unittest.TestCase):
    """Pure rendering of AnswerReport."""

    def _report(self, covered: bool = True) -> AnswerReport:
        with bundle(THREE_DOC_BUNDLE) as root:
            fake = FakeChat(COVERED_JSON if covered else UNCOVERED_JSON)
            return make_service(root, fake).answer("NATO alliance")

    def test_text_rendering_sections(self) -> None:
        text = render_text(self._report())
        for heading in ("## Current Situation", "## Key Developments", "## Key Actors", "## Evidence", "## Sources"):
            self.assertIn(heading, text)
        self.assertIn("https://www.nato.int/topic", text)

    def test_text_rendering_uncovered_exact_sentence(self) -> None:
        self.assertEqual(render_text(self._report(covered=False)), NOT_COVERED_SENTENCE)

    def test_json_rendering_stable_schema(self) -> None:
        payload = json.loads(render_json(self._report()))
        self.assertEqual(
            list(payload.keys()),
            ["answer", "reasoning", "documents_used", "evidence", "sources", "retrieval", "ranking", "generated_at", "provider", "model"],
        )
        self.assertEqual(
            list(payload["answer"].keys()),
            ["current_situation", "key_developments", "key_actors"],
        )
        self.assertEqual(
            list(payload["ranking"][0].keys()),
            ["document_id", "title_score", "tag_score", "id_score", "resource_score", "phrase_bonus", "total_score"],
        )
        self.assertEqual(
            list(payload["retrieval"].keys()),
            ["candidate_count", "selected_count", "selected_documents", "retrieval_time_ms"],
        )

    def test_deterministic_output(self) -> None:
        first = render_json(self._report())
        second = render_json(self._report())
        self.assertEqual(first, second)


class CLITests(unittest.TestCase):
    """ask command, flags, and exit-code mapping on stdout."""

    def _ask(self, argv: list[str], report: AnswerReport) -> tuple[int, str]:
        buffer = io.StringIO()
        with mock.patch("consumer_a.cli.ConsumerService") as service_cls:
            service_cls.return_value.answer.return_value = report
            with contextlib.redirect_stdout(buffer):
                code = main(argv)
        return code, buffer.getvalue()

    def test_ask_text_output(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            report = make_service(root).answer("NATO alliance")
        code, out = self._ask(["ask", "what", "is", "nato"], report)
        self.assertEqual(code, 0)
        self.assertIn("## Current Situation", out)

    def test_ask_json_output_and_max_docs(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            report = make_service(root).answer("NATO alliance")
        with mock.patch("consumer_a.cli.ConsumerService") as service_cls:
            service_cls.return_value.answer.return_value = report
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = main(["ask", "nato", "--json", "--max-docs", "2"])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertIn("answer", payload)
        service_cls.return_value.answer.assert_called_once_with("nato", max_docs=2)

    def test_invalid_arguments(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stderr(io.StringIO()):
                main(["ask", "nato", "--max-docs", "0"])
        self.assertEqual(ctx.exception.code, 2)

    def test_exit_code_mapping(self) -> None:
        self.assertEqual(exit_code_for(RetrievalError("x")), 2)
        self.assertEqual(exit_code_for(ConfigError("x")), 3)
        self.assertEqual(exit_code_for(LLMResponseError("x")), 4)
        self.assertEqual(exit_code_for(ProviderTimeoutError("x")), 4)
        self.assertEqual(exit_code_for(DocumentReadError("x")), 5)
        self.assertEqual(exit_code_for(FilesystemError("x")), 6)

    def test_config_error_exit_code(self) -> None:
        env = {"OKF_BUNDLE_PATH": "/nonexistent/bundle"}
        with mock.patch.dict(os.environ, env):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = main(["ask", "anything"])
        self.assertEqual(code, 3)
        self.assertIn("Bundle path does not exist", buffer.getvalue())

    def test_malformed_bundle_exit_code(self) -> None:
        with bundle({"actors/nato.md": "no frontmatter here\n"}) as root:
            env = {"OKF_BUNDLE_PATH": str(root)}
            with mock.patch.dict(os.environ, env):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = main(["ask", "nato"])
        self.assertEqual(code, 5)

    def test_empty_question_exit_code(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            with mock.patch.dict(os.environ, {"OKF_BUNDLE_PATH": str(root)}):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main(["ask", "   "])
        self.assertEqual(code, 2)


class LoggingTests(unittest.TestCase):
    """Structured logs: stages present, secrets and question never leaked."""

    def test_stage_logging_and_redaction(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            with self.assertLogs("consumer_a", level="INFO") as captured:
                make_service(root).answer("NATO alliance")
        text = "\n".join(captured.output)
        for stage in ("stage=retrieve", "stage=read", "stage=llm"):
            self.assertIn(stage, text)
        self.assertIn("question_hash=", text)
        self.assertNotIn("NATO alliance", text)
        self.assertNotIn("api_key", text.lower())


class RegressionAndPerformanceTests(unittest.TestCase):
    """Read-only guarantee, no caching, identical repeated behavior."""

    def test_consumer_a_never_writes(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            before = snapshot_tree(root)
            make_service(root).answer("NATO alliance")
            make_service(root).answer("What is the capital of France?")
            after = snapshot_tree(root)
        self.assertEqual(before, after)

    def test_no_bundle_caching(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            service = make_service(root)
            from consumer_a.reader import read_documents as real_read

            with mock.patch("consumer_a.service.read_documents", side_effect=real_read) as spy:
                service.answer("NATO alliance")
                service.answer("NATO alliance")
        self.assertEqual(spy.call_count, 2)  # bodies re-read every run


if __name__ == "__main__":
    unittest.main()
