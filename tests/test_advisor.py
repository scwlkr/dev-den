import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class AdvisorBuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dod-advisor-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "collection").mkdir()
        (self.root / "collection" / "roster.json").write_text(json.dumps({"developers": []}))

    def cli(self, *args, ok=True):
        r = subprocess.run(
            [sys.executable, "-B", "-m", "collection.advisor", "--project", str(self.root), *map(str, args)],
            cwd=REPO, text=True, capture_output=True,
        )
        if ok:
            self.assertEqual(r.returncode, 0, r.stderr + "\n" + r.stdout)
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            return {"exit": r.returncode, "error": r.stderr or r.stdout}

    def test_invalid_id_rejected(self):
        r = self.cli("prepare", "--id", "../evil", "--name", "X", "--focus", "y", ok=False)
        self.assertNotEqual(r.get("status"), "prepared")

    def test_duplicate_text_rejected(self):
        self.cli("prepare", "--id", "fixture", "--name", "Fixture", "--focus", "x", "--depth", "quick")
        f = self.root / "a.txt"
        f.write_text("Hello world " * 20)
        self.cli("import", "--id", "fixture", "--url", "https://example.org/a", "--text-file", f, "--title", "A")
        r = self.cli("import", "--id", "fixture", "--url", "https://example.org/b", "--text-file", f, "--title", "B")
        self.assertEqual(r.get("status"), "duplicate_text")

    def test_wrong_speaker_rejected(self):
        self.cli("prepare", "--id", "fixture", "--name", "Fixture", "--focus", "x", "--depth", "quick")
        f = self.root / "a.txt"
        f.write_text("Use a small working experiment to test constraints. " * 5)
        r = self.cli("import", "--id", "fixture", "--url", "https://example.org/a", "--text-file", f, "--title", "A")
        sid = r["source_id"]
        bad = {"eligible": True, "attribution": "speaker", "attribution_reason": "mismatch",
               "evidence": [{"kind": "principle", "claim": "x", "quote": f.read_text(), "context": "x", "speaker": "Another"}]}
        p = self.root / "bad.json"
        p.write_text(json.dumps(bad))
        r2 = self.cli("extraction-submit", "--id", "fixture", "--source-id", sid, "--file", p, ok=False)
        self.assertEqual(r2.get("status"), "rejected")


if __name__ == "__main__":
    unittest.main()
