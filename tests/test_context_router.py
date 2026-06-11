import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


SAMPLE_TEXT = """
Abstract
We propose a method for robust widgets.

1 Introduction
This paper studies widget routing.

2 Method
The model has an encoder, planner, and decoder. Figure 1 shows the pipeline.
Training uses supervised examples and inference uses beam search.

3 Experiments
We evaluate classification accuracy on WidgetSet test split. Table 1 reports accuracy.
The metric is accuracy, where higher is better. We compare against Baseline A.

4 Limitations
The method is slower on long documents.

Figure 1. Overall pipeline with encoder and decoder.
Table 1. Accuracy results on WidgetSet.
"""


class ContextRouterTests(unittest.TestCase):
    def test_builds_role_scoped_contexts_under_budget(self):
        from context_router import build_context_manifest

        manifest = build_context_manifest(SAMPLE_TEXT, char_budget=260)

        self.assertLessEqual(len(manifest["roles"]["method-analyst"]["context"]), 260)
        self.assertIn("encoder", manifest["roles"]["method-analyst"]["context"])
        self.assertNotIn("Accuracy results", manifest["roles"]["method-analyst"]["context"])

        experiment_context = manifest["roles"]["experiment-analyst"]["context"]
        self.assertLessEqual(len(experiment_context), 260)
        self.assertIn("accuracy", experiment_context.lower())
        self.assertIn("WidgetSet", experiment_context)

    def test_routes_figures_and_tables_to_specialized_roles(self):
        from context_router import build_context_manifest

        manifest = build_context_manifest(SAMPLE_TEXT, char_budget=220)

        self.assertEqual(manifest["figures"][0]["number"], "1")
        self.assertEqual(manifest["tables"][0]["number"], "1")
        self.assertIn("Figure 1", manifest["roles"]["figure-analyst"]["context"])
        self.assertIn("Table 1", manifest["roles"]["table-analyst"]["context"])
        self.assertIn("method-analyst", manifest["roles"]["writer"]["inputs"])
        self.assertIn("experiment-analyst", manifest["roles"]["writer"]["inputs"])


if __name__ == "__main__":
    unittest.main()
