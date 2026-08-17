"""Deterministic offline tests for Consumer B. No network access."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from consumer_b import NOT_COVERED_SENTENCE
from consumer_b.cli import exit_code_for, main
from consumer_b.exceptions import (
    ConfigError,
    DocumentReadError,
    FilesystemError,
    LLMResponseError,
    RetrievalError,
)
from consumer_b.exceptions import TimeoutError as ProviderTimeoutError
from consumer_b.llm import ChatClient, parse_analysis
from consumer_b.models import (
    BundleDocument,
    ConflictClaim,
    ConsumerConfig,
    DevelopmentEntry,
)
from consumer_b.renderer import render_json, render_text
from consumer_b.retriever import select
from consumer_b.service import ConsumerService
from consumer_b.verifier import verify_conflicts

REPO_ROOT = Path(__file__).resolve().parent.parent


def FIXED_CLOCK() -> datetime:
    return datetime(2026, 8, 6, 12, 0, 0, tzinfo=UTC)


ALPHA_CLAIM = "Russian forces are advancing steadily along the eastern front."
BETA_CLAIM = "Russian forces are not advancing and have lost ground since spring."

ALPHA_DOC = f"""---
schema_version: 1
id: frontline-alpha
type: concept
title: Frontline Alpha
resource: conflicts
tags: [russia, frontline]
created_at: 2026-08-01
last_updated: 2026-08-06
confidence: verified
related: [frontline-beta]
---

## Summary

{ALPHA_CLAIM}

## Developments

### 2026-08-06

Positions shifted near Donetsk.

## Key Actors

- Russia
- Ukraine

## Sources

- title: Alpha wire report
  url: https://alpha.example/report
  accessed: 2026-08-06
  note: Alpha desk.
"""

BETA_DOC = (
    ALPHA_DOC.replace("id: frontline-alpha", "id: frontline-beta")
    .replace("title: Frontline Alpha", "title: Frontline Beta")
    .replace("confidence: verified", "confidence: mixed")
    .replace("related: [frontline-beta]", "related: [frontline-alpha]")
    .replace(ALPHA_CLAIM, BETA_CLAIM)
    .replace("Alpha wire report", "Beta wire report")
    .replace("https://alpha.example/report", "https://beta.example/report")
)

GAMMA_DOC = (
    ALPHA_DOC.replace("id: frontline-alpha", "id: red-sea-brief")
    .replace("title: Frontline Alpha", "title: Red Sea Brief")
    .replace("tags: [russia, frontline]", "tags: [shipping]")
    .replace("related: [frontline-beta]", "related: []")
)

THREE_DOC_BUNDLE = {
    "conflicts/frontline-alpha.md": ALPHA_DOC,
    "conflicts/frontline-beta.md": BETA_DOC,
    "conflicts/red-sea-brief.md": GAMMA_DOC,
}


def analysis_json(**overrides) -> str:
    payload = {
        "assumptions": ["The bundle assumes open-source reporting is accurate."],
        "conflicting_evidence": [
            {
                "description": "Advance vs retreat",
                "documents": [1, 2],
                "supporting_text": ALPHA_CLAIM,
                "conflicting_text": BETA_CLAIM,
            }
        ],
        "uncertainties": ["Both assessments cite no troop counts."],
        "alternative_interpretations": ["'Lost ground' may refer to a limited sector only."],
        "missing_information": ["The bundle does not contain casualty figures."],
        "confidence_assessment": "Documents conflict directly; treat with caution.",
        "reasoning": "Both frontline documents were compared directly.",
    }
    payload.update(overrides)
    return json.dumps(payload)


class FakeChat:
    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self.text = text if text is not None else analysis_json()
        self.error = error
        self.calls = 0

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.text


class bundle:
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
    return ConsumerService(
        ConsumerConfig(bundle_path=bundle_path), llm_client=llm or FakeChat(), clock=FIXED_CLOCK
    )


def snapshot_tree(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def doc(id: str, title: str, summary: str) -> BundleDocument:
    return BundleDocument(
        id=id,
        title=title,
        resource="conflicts",
        relative_path=f"conflicts/{id}.md",
        summary=summary,
        developments=[DevelopmentEntry(date="2026-08-06", text=summary)],
        key_actors=["Russia"],
    )


class RetrievalTests(unittest.TestCase):
    """Deterministic scoring, ranking stability, diagnostics."""

    def test_scoring_and_deterministic_ranking(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            from consumer_b.reader import scan_catalog

            catalog = scan_catalog(root)
        result = select(catalog, "russia frontline", 3)
        self.assertEqual(
            [row.document_id for row in result.ranking],
            ["frontline-alpha", "frontline-beta"],
        )
        for row in result.ranking:
            self.assertEqual(
                row.title_score
                + row.tag_score
                + row.id_score
                + row.resource_score
                + row.phrase_bonus,
                row.total_score,
            )

    def test_identical_ranking_across_repeated_runs(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            first = make_service(root).analyze("russia frontline")
            second = make_service(root).analyze("russia frontline")
        self.assertEqual(render_json(first), render_json(second))

    def test_body_reads_only_for_selected_documents(self) -> None:
        from consumer_b.reader import read_documents as real_read

        with bundle(THREE_DOC_BUNDLE) as root:
            service = make_service(root)
            with mock.patch("consumer_b.service.read_documents", side_effect=real_read) as spy:
                report = service.analyze("russia frontline")
        self.assertEqual(spy.call_count, 1)
        read_ids = [entry.id for entry in spy.call_args.args[1]]
        self.assertEqual(read_ids, report.documents_used)
        self.assertNotIn("red-sea-brief", read_ids)

    def test_retrieval_diagnostics_correctness(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            report = make_service(root).analyze("russia frontline")
        self.assertEqual(report.retrieval.candidate_count, 3)
        self.assertEqual(report.retrieval.selected_count, len(report.documents_used))
        self.assertEqual(report.retrieval.selected_documents, report.documents_used)
        self.assertGreaterEqual(report.retrieval.retrieval_time_ms, 0)

    def test_five_theatre_multi_topic_decomposition(self) -> None:
        from consumer_b.reader import scan_catalog

        catalog = scan_catalog(REPO_ROOT / "okf")
        q = (
            "Assess the risk of a major geopolitical escalation involving Taiwan, the Strait of "
            "Hormuz, Gaza, Israel-Lebanon, and India-China. Rank the five situations by escalation "
            "risk using only evidence available in the OKF bundle, explain your reasoning, and "
            "identify where the bundle lacks sufficient evidence."
        )
        res = select(catalog, q, max_docs=3)
        selected_ids = [d.id for d in res.selected]
        self.assertGreaterEqual(len(selected_ids), 10)

        # Confirm representation from every single requested theatre
        has_taiwan = any("taiwan" in doc_id for doc_id in selected_ids)
        has_hormuz = any("hormuz" in doc_id or "irgc" in doc_id for doc_id in selected_ids)
        has_gaza = any("gaza" in doc_id or "hamas" in doc_id for doc_id in selected_ids)
        has_lebanon = any("lebanon" in doc_id or "hezbollah" in doc_id for doc_id in selected_ids)
        has_india_china = any("india" in doc_id or "arunachal" in doc_id for doc_id in selected_ids)

        self.assertTrue(has_taiwan, "Taiwan documents missing from multi-theatre retrieval")
        self.assertTrue(has_hormuz, "Hormuz documents missing from multi-theatre retrieval")
        self.assertTrue(has_gaza, "Gaza documents missing from multi-theatre retrieval")
        self.assertTrue(
            has_lebanon, "Israel-Lebanon documents missing from multi-theatre retrieval"
        )
        self.assertTrue(
            has_india_china, "India-China documents missing from multi-theatre retrieval"
        )

    def test_uncovered_query_returns_empty_selection(self) -> None:
        from consumer_b.reader import scan_catalog

        catalog = scan_catalog(REPO_ROOT / "okf")
        q = "What are the lithium extraction royalty rates in Salar de Atacama?"
        res = select(catalog, q, max_docs=3)
        self.assertEqual(len(res.selected), 0)


class VerifierTests(unittest.TestCase):
    """Verbatim conflict verification against retrieved documents only."""

    def _claim(self, docs=(1, 2), supporting=ALPHA_CLAIM, conflicting=BETA_CLAIM) -> ConflictClaim:
        return ConflictClaim(
            description="Advance vs retreat",
            documents=list(docs),
            supporting_text=supporting,
            conflicting_text=conflicting,
        )

    def test_valid_conflict_resolution_and_traceability(self) -> None:
        documents = [
            doc("frontline-alpha", "Frontline Alpha", ALPHA_CLAIM),
            doc("frontline-beta", "Frontline Beta", BETA_CLAIM),
        ]
        verified, discarded = verify_conflicts([self._claim()], documents)
        self.assertEqual(len(verified), 1)
        self.assertEqual(discarded, [])
        self.assertEqual(verified[0].document_ids, ["frontline-alpha", "frontline-beta"])
        self.assertEqual(verified[0].supporting_text, ALPHA_CLAIM)

    def test_invalid_document_index(self) -> None:
        documents = [doc("a", "A", ALPHA_CLAIM)]
        verified, discarded = verify_conflicts([self._claim(docs=(1, 5))], documents)
        self.assertEqual(verified, [])
        self.assertIn("out of range", discarded[0])

    def test_supporting_snippet_not_found(self) -> None:
        documents = [doc("a", "A", ALPHA_CLAIM)]
        verified, discarded = verify_conflicts(
            [self._claim(docs=(1,), supporting="not in the bundle", conflicting=ALPHA_CLAIM)],
            documents,
        )
        self.assertEqual(verified, [])
        self.assertIn("supporting_text", discarded[0])

    def test_one_valid_one_invalid_snippet_is_discarded(self) -> None:
        documents = [doc("a", "A", ALPHA_CLAIM), doc("b", "B", BETA_CLAIM)]
        verified, discarded = verify_conflicts(
            [self._claim(supporting=ALPHA_CLAIM, conflicting="fabricated quote")], documents
        )
        self.assertEqual(verified, [])
        self.assertIn("conflicting_text", discarded[0])

    def test_duplicate_conflict_elimination(self) -> None:
        documents = [
            doc("frontline-alpha", "Frontline Alpha", ALPHA_CLAIM),
            doc("frontline-beta", "Frontline Beta", BETA_CLAIM),
        ]
        verified, discarded = verify_conflicts([self._claim(), self._claim()], documents)
        self.assertEqual(len(verified), 1)
        self.assertTrue(any("duplicate" in reason for reason in discarded))

    def test_verification_scans_only_retrieved_documents(self) -> None:
        """A quote existing only in a NON-retrieved document must not verify."""

        documents = [doc("frontline-alpha", "Frontline Alpha", ALPHA_CLAIM)]
        verified, discarded = verify_conflicts(
            [self._claim(docs=(1,), supporting=ALPHA_CLAIM, conflicting=BETA_CLAIM)],
            documents,
        )
        self.assertEqual(verified, [])
        self.assertTrue(discarded)


class LLMContractTests(unittest.TestCase):
    """parse_analysis strictness and client error mapping."""

    def test_valid_response(self) -> None:
        analysis = parse_analysis(analysis_json())
        self.assertEqual(
            analysis.missing_information, ["The bundle does not contain casualty figures."]
        )

    def test_malformed_json(self) -> None:
        with self.assertRaises(LLMResponseError):
            parse_analysis("not json {")

    def test_code_fences_rejected(self) -> None:
        with self.assertRaisesRegex(LLMResponseError, "code fence"):
            parse_analysis(f"```json\n{analysis_json()}\n```")

    def test_unexpected_fields_rejected(self) -> None:
        payload = json.loads(analysis_json())
        payload["sources"] = ["https://invented.example"]
        with self.assertRaises(LLMResponseError):
            parse_analysis(json.dumps(payload))

    def test_urls_and_citations_rejected(self) -> None:
        for bad in ("see https://x.example", "see www.x.example", "claim [1]"):
            payload = json.loads(analysis_json())
            payload["assumptions"] = [bad]
            with self.assertRaises(LLMResponseError):
                parse_analysis(json.dumps(payload))

    def test_yaml_and_headings_rejected(self) -> None:
        for bad in ("line --- break", "# Heading"):
            payload = json.loads(analysis_json())
            payload["reasoning"] = bad
            with self.assertRaises(LLMResponseError):
                parse_analysis(json.dumps(payload))

    def test_schema_validation_errors(self) -> None:
        for broken in ('{"assumptions": []}', "[1, 2]", '"text"'):
            with self.assertRaises(LLMResponseError):
                parse_analysis(broken)

    def test_timeout_maps_to_timeout_error(self) -> None:
        client = ChatClient.__new__(ChatClient)
        client._model = "m"

        class Completions:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("request timed out after 30s")

        client._client = type("S", (), {"chat": type("C", (), {"completions": Completions})()})()
        with self.assertRaises(ProviderTimeoutError):
            client.chat("s", "u")

    def test_authentication_failure_is_clear(self) -> None:
        client = ChatClient.__new__(ChatClient)
        client._model = "m"
        client._key_env = "OPENAI_API_KEY"

        class Completions:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("401 Unauthorized: invalid api key")

        client._client = type("S", (), {"chat": type("C", (), {"completions": Completions})()})()
        with self.assertRaisesRegex(LLMResponseError, "authentication failed"):
            client.chat("s", "u")

    def test_missing_key_names_provider_key_env(self) -> None:
        with self.assertRaisesRegex(ConfigError, "OPENAI_API_KEY"):
            ChatClient(ConsumerConfig(bundle_path=Path("."), provider="openai"))
        with self.assertRaisesRegex(ConfigError, "GROQ_API_KEY"):
            ChatClient(ConsumerConfig(bundle_path=Path("."), provider="groq"))


class ServiceTests(unittest.TestCase):
    """End-to-end orchestration through ConsumerService.analyze."""

    def test_covered_question_full_analysis(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            report = make_service(root).analyze("russia frontline")
        self.assertTrue(report.covered)
        self.assertEqual(report.documents_used, ["frontline-alpha", "frontline-beta"])
        analysis = report.critical_analysis
        self.assertEqual(
            analysis.assumptions, ["The bundle assumes open-source reporting is accurate."]
        )
        self.assertEqual(len(analysis.conflicting_evidence), 1)
        self.assertEqual(
            analysis.missing_information, ["The bundle does not contain casualty figures."]
        )
        self.assertEqual(
            analysis.confidence_assessment, "Documents conflict directly; treat with caution."
        )
        self.assertEqual(report.evidence[0].confidence, "verified")
        self.assertEqual(report.sources[0].accessed_date, "2026-08-06")
        self.assertEqual(report.bundle_version, 1)
        self.assertEqual(report.generated_at, "2026-08-06T12:00:00+00:00")

    def test_unverifiable_conflicts_discarded_not_fatal(self) -> None:
        fake = FakeChat(
            analysis_json(
                conflicting_evidence=[
                    {
                        "description": "ok",
                        "documents": [1, 2],
                        "supporting_text": ALPHA_CLAIM,
                        "conflicting_text": BETA_CLAIM,
                    },
                    {
                        "description": "dup",
                        "documents": [1, 2],
                        "supporting_text": ALPHA_CLAIM,
                        "conflicting_text": BETA_CLAIM,
                    },
                    {
                        "description": "bad index",
                        "documents": [9],
                        "supporting_text": ALPHA_CLAIM,
                        "conflicting_text": BETA_CLAIM,
                    },
                    {
                        "description": "fabricated",
                        "documents": [1],
                        "supporting_text": "never wrote this",
                        "conflicting_text": "nor this",
                    },
                ]
            )
        )
        with self.assertLogs("consumer_b", level="INFO") as captured:
            with bundle(THREE_DOC_BUNDLE) as root:
                report = make_service(root, fake).analyze("russia frontline")
        self.assertTrue(report.covered)
        resolved = report.critical_analysis.conflicting_evidence
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].description, "ok")
        text = "\n".join(captured.output)
        self.assertIn("verified_conflicts=1", text)
        self.assertIn("discarded_conflicts=3", text)

    def test_retrieval_uncovered_makes_zero_llm_calls(self) -> None:
        fake = FakeChat()
        with bundle(THREE_DOC_BUNDLE) as root:
            report = make_service(root, fake).analyze("What is the capital of France?")
        self.assertEqual(fake.calls, 0)
        self.assertFalse(report.covered)
        self.assertEqual(report.critical_analysis.confidence_assessment, NOT_COVERED_SENTENCE)
        self.assertIsNone(report.bundle_version)
        self.assertEqual(report.sources, [])

    def test_llm_declared_uncovered(self) -> None:
        fake = FakeChat(
            analysis_json(
                assumptions=[],
                conflicting_evidence=[],
                uncertainties=[],
                alternative_interpretations=[],
                missing_information=[],
                confidence_assessment=NOT_COVERED_SENTENCE,
                reasoning="",
            )
        )
        with bundle(THREE_DOC_BUNDLE) as root:
            report = make_service(root, fake).analyze("russia frontline")
        self.assertEqual(fake.calls, 1)
        self.assertFalse(report.covered)
        self.assertEqual(report.documents_used, ["frontline-alpha", "frontline-beta"])

    def test_malformed_bundle_no_frontmatter(self) -> None:
        with bundle({"conflicts/a.md": "## prose only\n"}) as root:
            with self.assertRaises(DocumentReadError):
                make_service(root).analyze("russia")

    def test_duplicate_ids_rejected(self) -> None:
        with bundle({"conflicts/a.md": ALPHA_DOC, "actors/a-copy.md": ALPHA_DOC}) as root:
            with self.assertRaisesRegex(DocumentReadError, "duplicate"):
                make_service(root).analyze("russia")

    def test_invalid_yaml_rejected(self) -> None:
        broken = ALPHA_DOC.replace("tags: [russia, frontline]", "tags: [russia")
        with bundle({"conflicts/a.md": broken}) as root:
            with self.assertRaisesRegex(DocumentReadError, "YAML"):
                make_service(root).analyze("russia")

    def test_filesystem_failure(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            with mock.patch.object(Path, "read_text", side_effect=OSError("disk gone")):
                with self.assertRaises(FilesystemError):
                    make_service(root).analyze("russia frontline")

    def test_mixed_schema_versions_null_bundle_version(self) -> None:
        beta_v2 = BETA_DOC.replace("schema_version: 1", "schema_version: 2")
        with bundle(
            {"conflicts/frontline-alpha.md": ALPHA_DOC, "conflicts/frontline-beta.md": beta_v2}
        ) as root:
            with self.assertLogs("consumer_b", level="WARNING"):
                report = make_service(root).analyze("russia frontline")
        self.assertIsNone(report.bundle_version)

    def test_malformed_confidence_field_coerced(self) -> None:
        weird = ALPHA_DOC.replace("confidence: verified", "confidence: [unusually, structured]")
        with bundle({"conflicts/frontline-alpha.md": weird}) as root:
            report = make_service(root).analyze("russia frontline")
        self.assertTrue(report.covered)  # no crash; confidence coerced to text

    def test_malformed_source_metadata_dropped(self) -> None:
        broken = ALPHA_DOC.replace(
            "- title: Alpha wire report\n  url: https://alpha.example/report\n",
            "- title: Alpha wire report\n",
        )
        with bundle({"conflicts/frontline-alpha.md": broken}) as root:
            report = make_service(root).analyze("russia frontline")
        self.assertEqual(report.sources, [])  # url-less source is not citable

    def test_identical_output_across_repeated_runs(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            first_dict = json.loads(render_json(make_service(root).analyze("russia frontline")))
            second_dict = json.loads(render_json(make_service(root).analyze("russia frontline")))
            first_dict["retrieval"]["retrieval_time_ms"] = 0
            second_dict["retrieval"]["retrieval_time_ms"] = 0
        self.assertEqual(first_dict, second_dict)

    def test_llm_never_receives_sources_or_ids(self) -> None:
        captured: list[str] = []

        class CapturingChat(FakeChat):
            def chat(self, system_prompt, user_prompt):
                captured.append(user_prompt)
                return super().chat(system_prompt, user_prompt)

        with bundle(THREE_DOC_BUNDLE) as root:
            make_service(root, CapturingChat()).analyze("russia frontline")
        prompt = captured[0]
        self.assertNotIn("https://", prompt)
        self.assertNotIn(".md", prompt)
        self.assertNotIn("Sources:", prompt)


class RendererTests(unittest.TestCase):
    def _report(self, covered: bool = True):
        fake = FakeChat(
            analysis_json()
            if covered
            else analysis_json(
                assumptions=[],
                conflicting_evidence=[],
                uncertainties=[],
                alternative_interpretations=[],
                missing_information=[],
                confidence_assessment=NOT_COVERED_SENTENCE,
                reasoning="",
            )
        )
        with bundle(THREE_DOC_BUNDLE) as root:
            return make_service(root, fake).analyze("russia frontline")

    def test_text_rendering_sections(self) -> None:
        text = render_text(self._report())
        for heading in (
            "## Confidence Assessment",
            "## Assumptions",
            "## Conflicting Evidence",
            "## Uncertainties",
            "## Alternative Interpretations",
            "## Missing Information",
            "## Evidence",
            "## Sources",
        ):
            self.assertIn(heading, text)
        self.assertIn("frontline-alpha, frontline-beta", text)

    def test_text_rendering_uncovered_exact_sentence(self) -> None:
        self.assertEqual(render_text(self._report(covered=False)), NOT_COVERED_SENTENCE)

    def test_json_schema_stability_and_key_ordering(self) -> None:
        payload = json.loads(render_json(self._report()))
        self.assertEqual(
            list(payload.keys()),
            [
                "critical_analysis",
                "reasoning",
                "documents_used",
                "evidence",
                "sources",
                "retrieval",
                "ranking",
                "generated_at",
                "provider",
                "model",
                "bundle_version",
            ],
        )
        self.assertEqual(
            list(payload["critical_analysis"].keys()),
            [
                "assumptions",
                "conflicting_evidence",
                "uncertainties",
                "alternative_interpretations",
                "missing_information",
                "confidence_assessment",
            ],
        )
        self.assertEqual(
            list(payload["critical_analysis"]["conflicting_evidence"][0].keys()),
            ["description", "document_ids", "supporting_text", "conflicting_text"],
        )

    def test_deterministic_rendering(self) -> None:
        report = self._report()
        self.assertEqual(render_json(report), render_json(report))


class CLITests(unittest.TestCase):
    def _report(self):
        with bundle(THREE_DOC_BUNDLE) as root:
            return make_service(root).analyze("russia frontline")

    def test_analyze_text_output(self) -> None:
        report = self._report()
        with mock.patch("consumer_b.cli.ConsumerService") as cls:
            cls.return_value.analyze.return_value = report
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = main(["analyze", "how", "reliable", "is", "this"])
        self.assertEqual(code, 0)
        self.assertIn("## Conflicting Evidence", buf.getvalue())

    def test_analyze_json_and_max_docs(self) -> None:
        report = self._report()
        with mock.patch("consumer_b.cli.ConsumerService") as cls:
            cls.return_value.analyze.return_value = report
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = main(["analyze", "frontline", "--json", "--max-docs", "2"])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertIn("critical_analysis", payload)
        cls.return_value.analyze.assert_called_once_with("frontline", max_docs=2)

    def test_invalid_arguments(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stderr(io.StringIO()):
                main(["analyze", "frontline", "--max-docs", "0"])
        self.assertEqual(ctx.exception.code, 2)

    def test_exit_code_mapping(self) -> None:
        self.assertEqual(exit_code_for(RetrievalError("x")), 2)
        self.assertEqual(exit_code_for(ConfigError("x")), 3)
        self.assertEqual(exit_code_for(LLMResponseError("x")), 4)
        self.assertEqual(exit_code_for(ProviderTimeoutError("x")), 4)
        self.assertEqual(exit_code_for(DocumentReadError("x")), 5)
        self.assertEqual(exit_code_for(FilesystemError("x")), 6)

    def test_config_error_exit_code(self) -> None:
        with mock.patch.dict(os.environ, {"OKF_BUNDLE_PATH": "/nonexistent/bundle"}):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = main(["analyze", "anything"])
        self.assertEqual(code, 3)
        self.assertIn("Bundle path does not exist", buf.getvalue())

    def test_malformed_bundle_exit_code(self) -> None:
        with bundle({"conflicts/a.md": "no frontmatter\n"}) as root:
            with mock.patch.dict(os.environ, {"OKF_BUNDLE_PATH": str(root)}):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main(["analyze", "russia"])
        self.assertEqual(code, 5)

    def test_empty_question_exit_code(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            with mock.patch.dict(os.environ, {"OKF_BUNDLE_PATH": str(root)}):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main(["analyze", "   "])
        self.assertEqual(code, 2)


class LoggingTests(unittest.TestCase):
    def test_stage_logging_and_redaction(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            with self.assertLogs("consumer_b", level="INFO") as captured:
                make_service(root).analyze("russia frontline")
        text = "\n".join(captured.output)
        for stage in ("stage=retrieve", "stage=read", "stage=llm", "stage=verify"):
            self.assertIn(stage, text)
        self.assertIn("question_hash=", text)
        self.assertNotIn("NATO ", text)
        self.assertNotIn("api_key", text.lower())


class RegressionAndPerformanceTests(unittest.TestCase):
    def test_consumer_b_never_writes(self) -> None:
        with bundle(THREE_DOC_BUNDLE) as root:
            before = snapshot_tree(root)
            make_service(root).analyze("russia frontline")
            make_service(root).analyze("What is the capital of France?")
            after = snapshot_tree(root)
        self.assertEqual(before, after)

    def test_no_bundle_caching(self) -> None:
        from consumer_b.reader import read_documents as real_read

        with bundle(THREE_DOC_BUNDLE) as root:
            service = make_service(root)
            with mock.patch("consumer_b.service.read_documents", side_effect=real_read) as spy:
                service.analyze("russia frontline")
                service.analyze("russia frontline")
        self.assertEqual(spy.call_count, 2)


if __name__ == "__main__":
    unittest.main()
