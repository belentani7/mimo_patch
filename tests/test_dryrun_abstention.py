"""Regression: dry-run cannot invent IGNORE_SPAM for unrelated tasks."""
import json
import subprocess
import sys
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
def dry(state):
    p = subprocess.run([sys.executable,str(ROOT/"mimo_patch.py"),"dry-run","--state",state],cwd=ROOT,capture_output=True,text=True,timeout=12)
    if p.returncode: raise AssertionError(p.stderr)
    return json.loads(p.stdout)
class TestDryRunAbstention(unittest.TestCase):
    def test_unknown_coding_task_abstains(self):
        x=dry("Fix React build error")
        self.assertIsNone(x["chosen_action"])
        self.assertEqual(x["confidence"],0.0)
        self.assertEqual(x["plan"],"ASK_CLARIFICATION")
        self.assertTrue(x["dry_run"])
    def test_unknown_music_task_abstains(self):
        x=dry("Generate a WebGL music galaxy using Three.js")
        self.assertIsNone(x["chosen_action"])
        self.assertEqual(x["confidence"],0.0)
    def test_known_spam_remains_classified(self):
        x=dry("GANADOR! Tu premio gratis, click here")
        self.assertEqual(x["chosen_action"],"ignore_spam")
    def test_provider_not_called(self):
        x=dry("Fix React build error")
        self.assertEqual(x["logic_trace"],"dry_run_no_provider_call")
if __name__=="__main__":unittest.main()
