import json
from pathlib import Path
import tempfile
import unittest

from collection.pilot import PageText, Pilot, SECTIONS, canonical, get_course, verify_evidence


QUOTE = "Choose the simplest implementation that meets the actual requirements."
TEXT = "Written by Test Developer.\n" + QUOTE + "\n" + "A discussion of context and software design trade-offs. " * 30


class FakeProvider:
    def __init__(self):
        self.calls = []

    def __call__(self, req):
        stage = req["text"]["format"]["name"]
        self.calls.append(stage)
        if stage == "dod_discover":
            value = {"sources": [
                {"url": "https://example.org/wrong", "title": "Wrong quotation", "reason": "candidate"},
                {"url": "https://example.org/good", "title": "Good essay", "reason": "candidate"},
            ], "gaps": []}
        elif stage == "dod_extract":
            payload = json.loads(req["input"][req["input"].index('{"candidate"'):])
            quote = QUOTE if payload["candidate"]["url"].endswith("good") else "This sentence is not present in the retained source text."
            value = {"eligible": True, "attribution": "sole_author", "attribution_reason": "Byline identifies Test Developer", "title": "Test source", "date": "", "topics": ["simplicity"], "limitations": [],
                     "evidence": [{"kind": "principle", "claim": "Prefer simple implementations within requirements", "quote": quote, "context": "Qualified by actual requirements", "speaker": "Test Developer"}]}
        else:
            payload = json.loads(req["input"][req["input"].index('{"evidence"'):])
            evidence_id = payload["evidence"][0]["id"]
            value = {"sections": [{"name": name, "items": [{"text": "Prefer simplicity within the actual constraints.", "basis": "documented", "evidence_ids": [evidence_id]}] if name in ("_hot", "principles") else []} for name in SECTIONS], "gaps": ["Only one source in this test collection"]}
        return {"id": "resp_fixture", "status": "completed", "usage": {"input_tokens": 100, "output_tokens": 100}, "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(value)}]}]}


def fetch_fixture(url):
    return {"text": TEXT + (" distinct wrong candidate" if url.endswith("wrong") else ""), "metadata": {"url": url, "title": "Test source"}, "links": []}


def config():
    return {"model": "gpt-6.1-terra", "budget_usd": 25, "target_sources": 1, "max_candidates": 2, "discovery_tool_calls": 3,
            "pricing": {"input_per_million": 1, "output_per_million": 5, "web_search_per_call": .01},
            "developers": [{"id": "test", "name": "Test Developer", "seeds": ["https://example.org/"], "focus": "software simplicity"}]}


class CollectionBehavior(unittest.TestCase):
    def test_pipeline_retains_evidence_rejects_fabrication_compiles_and_resumes_without_paid_work(self):
        with tempfile.TemporaryDirectory(prefix="dod-test-") as tmp:
            root = Path(tmp)
            (root / "collection").mkdir()
            provider = FakeProvider()
            report = Pilot(root, config(), provider, fetch_fixture).run()
            self.assertEqual(report["status"], "completed")
            dev = report["developers"][0]
            self.assertEqual((dev["accepted_sources"], dev["held_out"], dev["verified_passages"], dev["rejected_passages"]), (1, 1, 1, 1))
            self.assertTrue((root / "knowledge/test/principles.md").is_file())
            compiled = (root / "knowledge/test/principles.md").read_text()
            self.assertIn("https://example.org/good", compiled)
            self.assertNotIn("not present in the retained", compiled)
            excerpts = (root / "knowledge/test/sources.md").read_text()
            self.assertIn("> " + " ".join(QUOTE.split()[:22]), excerpts)
            sources = list((root / ".collection/pilot/test/sources").glob("*/source.txt"))
            self.assertEqual(len(sources), 2)
            before = len(provider.calls)
            resumed = Pilot(root, config(), provider, fetch_fixture).run()
            self.assertEqual(len(provider.calls), before)
            self.assertEqual(resumed["accounted_exposure_usd"], report["accounted_exposure_usd"])

    def test_budget_reservation_stops_before_paid_request(self):
        with tempfile.TemporaryDirectory(prefix="dod-test-") as tmp:
            root = Path(tmp)
            (root / "collection").mkdir()
            cfg = config()
            cfg["budget_usd"] = .001
            provider = FakeProvider()
            report = Pilot(root, cfg, provider, fetch_fixture).run()
            self.assertTrue(report["status"].startswith("stopped:"))
            self.assertEqual(provider.calls, [])
            self.assertEqual(report["accounted_exposure_usd"], 0)

    def test_uncertain_charge_is_reserved_and_never_retried(self):
        with tempfile.TemporaryDirectory(prefix="dod-test-") as tmp:
            root = Path(tmp)
            (root / "collection").mkdir()
            calls = []
            def timed_out(req):
                calls.append(req)
                raise TimeoutError("request may have reached provider")
            first = Pilot(root, config(), timed_out, fetch_fixture).run()
            self.assertEqual(len(calls), 1)
            self.assertGreater(first["accounted_exposure_usd"], 0)
            second = Pilot(root, config(), timed_out, fetch_fixture).run()
            self.assertEqual(len(calls), 1)
            self.assertEqual(second["accounted_exposure_usd"], first["accounted_exposure_usd"])

    def test_other_author_is_not_promoted_even_when_quote_matches(self):
        raw = {"eligible": True, "attribution": "other_author", "attribution_reason": "An interviewer said this", "evidence": [{"quote": QUOTE}]}
        good, rejected = verify_evidence("source", "test", TEXT, raw)
        self.assertEqual(good, [])
        self.assertTrue(rejected)

    def test_a_real_quote_from_another_source_does_not_verify(self):
        raw = {"eligible": True, "attribution": "sole_author", "evidence": [{"quote": QUOTE, "claim": "misattributed"}]}
        good, rejected = verify_evidence("wrong-source", "test", "Different source with entirely different text.", raw)
        self.assertEqual(good, [])
        self.assertEqual(len(rejected), 1)

    def test_interviewer_words_are_rejected_when_mislabeled_as_the_target(self):
        raw = {"eligible": True, "attribution": "speaker", "evidence": [{"quote": QUOTE, "speaker": "Interviewer", "claim": "A different speaker's view"}]}
        good, rejected = verify_evidence("interview", "test", TEXT, raw, ["Test Developer"])
        self.assertEqual(good, [])
        self.assertEqual(len(rejected), 1)

    def test_page_extraction_preserves_speakers_and_code_without_navigation(self):
        p = PageText()
        p.feed('<html><nav>Ignore navigation</nav><article><h1>Interview</h1><p>Test Developer:</p><p>' + TEXT + '</p><pre>if (ready) { run(); }</pre><p>Interviewer:</p><p>A separate view.</p></article></html>')
        self.assertNotIn("Ignore navigation", p.text())
        self.assertIn("Test Developer:", p.text())
        self.assertIn("Interviewer:", p.text())
        self.assertIn("if (ready) { run(); }", p.text())

    def test_code_indentation_is_preserved(self):
        p = PageText()
        p.feed('<html><body><pre>def ready():\n    return True\n</pre></body></html>')
        self.assertIn('def ready():\n    return True', p.text())

    def test_publication_date_outside_article_is_retained_as_metadata(self):
        p = PageText()
        p.feed('<html><body><header><time datetime="2024-02-01" itemprop="datePublished">February 1</time></header><article>' + TEXT + '</article></body></html>')
        self.assertIn({'datetime':'2024-02-01','itemprop':'datePublished'},p.metadata['time_elements'])

    def test_course_is_one_work_with_linked_content_and_no_cross_site_fetches(self):
        seen = []
        def fetch(url):
            seen.append(url)
            if url.endswith('/fem-git/'):
                return {'text': 'Course by ThePrimeagen', 'metadata': {'url':url}, 'links': [
                    {'url':'https://theprimeagen.github.io/fem-git/lesson','title':'A lesson'},
                    {'url':'https://other.example/advert','title':'Not part of the course'},
                ]}
            return {'text': TEXT, 'metadata': {'url':url}, 'links': []}
        course = get_course('https://theprimeagen.github.io/fem-git/', fetch)
        self.assertEqual(len(course['metadata']['parts']),1)
        self.assertIn(QUOTE, course['text'])
        self.assertEqual(course['metadata']['collection_version'],'linked-course-1')
        self.assertEqual(len(seen),2)

    def test_youtube_fragments_do_not_create_separate_sources(self):
        self.assertEqual(canonical("https://youtu.be/abc123?t=10&utm_source=test"), canonical("https://www.youtube.com/watch?v=abc123&t=20"))


if __name__ == "__main__":
    unittest.main()
