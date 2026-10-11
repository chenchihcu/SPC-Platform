"""Exercise the routing data through its real PowerShell consumer.

Disposable negative fixtures are kept under SPC_ROUTER_TEST_ROOT (or the OS
temporary directory); this test never changes the live routing table.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / ".agents/skills/spc-change-router/route-table.json"
PROJECTION = ROOT / ".claude/skills/spc-change-router/route-table.json"
HOOK = ROOT / ".claude/hooks/changed-path-advisor.ps1"
ENGINES = [
    path
    for path in (
        shutil.which("pwsh"),
        str(Path(os.environ.get("WINDIR", r"C:\Windows"))
            / "System32/WindowsPowerShell/v1.0/powershell.exe"),
    )
    if path and Path(path).is_file()
]


class ChangeRouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ENGINES:
            raise unittest.SkipTest("PowerShell is required to verify the hook")
        cls.table = json.loads(CANONICAL.read_text(encoding="utf-8-sig"))

    def run_script(self, engine, script, payload=""):
        env = os.environ.copy()
        # os.environ normalizes names to uppercase on Windows. Do not carry a
        # PowerShell 7 module path into a Windows PowerShell 5 child.
        for name in tuple(env):
            if name.casefold() == "psmodulepath":
                env.pop(name)
        completed = subprocess.run(
            [engine, "-NoProfile", "-File", str(script)],
            input=payload,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            cwd=ROOT,
            env=env,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertEqual(completed.stderr, "")
        return completed.stdout.strip()

    def context(self, engine, path, hook=HOOK):
        payload = json.dumps({"tool_input": {"file_path": path}})
        output = self.run_script(engine, hook, payload)
        if not output:
            return ""
        result = json.loads(output)
        self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "PostToolBatch")
        return result["hookSpecificOutput"]["additionalContext"]

    def test_canonical_projection_and_document_targets(self):
        self.assertEqual(CANONICAL.read_bytes(), PROJECTION.read_bytes())
        self.assertEqual(
            {surface["key"] for surface in self.table["surfaces"]},
            {"ui-theme", "analytics", "report-export", "docs-harness", "release"},
        )
        for surface in self.table["surfaces"]:
            for doc in surface["docs"]:
                with self.subTest(surface=surface["key"], doc=doc):
                    self.assertTrue((ROOT / doc).is_file(), f"Missing route document: {doc}")

    def test_v3_and_launch_conditions_are_explicit(self):
        for surface in self.table["surfaces"]:
            for gate in surface["gates"]:
                with self.subTest(surface=surface["key"], gate=gate["cmd"]):
                    if re.search(r"-m\s+pytest\s+-q\s*(?:$|;)", gate["cmd"]):
                        self.assertIn("V3", gate["when"])
                    if "check_launch.py" in gate["cmd"]:
                        self.assertTrue(gate["when"].strip(), "Launch must follow invalidated surfaces")

    def test_all_route_surfaces_and_special_filenames(self):
        cases = [
            ("app/ui/panel.py", "qt-ui-token-auditor"),
            ("app/charts/histogram_chart.py", "qt-ui-token-auditor"),
            (".claude/rules/ui_theme.md", "qt-ui-token-auditor"),
            (".cursor/rules/ui_theme.mdc", "qt-ui-token-auditor"),
            ("app/analytics/capability_engine.py", "spc-stat-contract-reviewer"),
            ("chart_registry.py", "spc-stat-contract-reviewer"),
            ("app/viewmodels/chart_analysis_viewmodel.py", "spc-stat-contract-reviewer"),
            ("scripts/validate_db_chart_semantics.py", "spc-stat-contract-reviewer"),
            ("docs/governance/SPC_RULES.md", "spc-stat-contract-reviewer"),
            ("app/services/report_context.py", "report-export-parity-reviewer"),
            ("app/services/pptx_report_builder.py", "report-export-parity-reviewer"),
            ("app/services/diagnostic_excel_exporter.py", "report-export-parity-reviewer"),
            ("docs/harness/README.md", "scripts/harness_check.ps1"),
            ("AGENTS.md", "scripts/harness_check.ps1"),
            ("CLAUDE.md", "scripts/harness_check.ps1"),
            (".agents/skills/example/SKILL.md", "scripts/harness_check.ps1"),
            (".claude/skills/example/SKILL.md", "scripts/harness_check.ps1"),
            (".cursor/rules/example.mdc", "scripts/harness_check.ps1"),
            (".codex/rules/project.rules", "scripts/harness_check.ps1"),
            ("scripts/harness_check.ps1", "scripts/harness_check.ps1"),
            ("scripts/run_release_gate.py", "scripts/run_release_gate.py"),
        ]
        for engine in ENGINES:
            for path, expected in cases:
                with self.subTest(engine=engine, path=path):
                    self.assertIn(expected, self.context(engine, path))

    def test_windows_absolute_and_mixed_separators(self):
        paths = [
            r"app\analytics\capability_engine.py",
            r"C:\Users\user\Documents\SPC Platform\app\analytics\capability_engine.py",
            r"C:/Users/user/Documents/SPC Platform\app/analytics\capability_engine.py",
        ]
        for engine in ENGINES:
            for path in paths:
                with self.subTest(engine=engine, path=path):
                    self.assertIn("spc-stat-contract-reviewer", self.context(engine, path))

    def test_overlapping_routes_and_unstructured_fallback(self):
        for engine in ENGINES:
            with self.subTest(engine=engine):
                context = self.context(engine, "docs/governance/SPC_RULES.md")
                self.assertIn("spc-stat-contract-reviewer", context)
                self.assertIn("scripts/harness_check.ps1", context)
                self.assertEqual(context.count("Read/confirm source docs:"), 1)
                self.assertEqual(context.count("docs/governance/SPC_RULES.md"), 1)
                self.assertIn("V3 only", context)
                output = self.run_script(engine, HOOK, "Changed docs/harness/README.md")
                self.assertIn("scripts/harness_check.ps1", output)

    def test_unrelated_and_near_match_paths_remain_quiet(self):
        for engine in ENGINES:
            for path in ("assets/logo.svg", "notes/AGENTS.md.bak", "chart_registryXpy"):
                with self.subTest(engine=engine, path=path):
                    self.assertEqual(self.context(engine, path), "")
            self.assertEqual(self.run_script(engine, HOOK), "")

    def test_missing_or_invalid_json_reports_inactive(self):
        for contents in (None, "{broken", "{}", '{"surfaces": [{}]}', '{"surfaces": [{"pathRegex": "["}]}'):
            fixture = Path(tempfile.mkdtemp(prefix="spc-router-", dir=os.environ.get("SPC_ROUTER_TEST_ROOT")))
            fixture_hook = fixture / ".claude/hooks/changed-path-advisor.ps1"
            fixture_hook.parent.mkdir(parents=True)
            shutil.copyfile(HOOK, fixture_hook)
            if contents is not None:
                table = fixture / ".claude/skills/spc-change-router/route-table.json"
                table.parent.mkdir(parents=True)
                table.write_text(contents, encoding="utf-8")
            for engine in ENGINES:
                with self.subTest(engine=engine, contents=contents):
                    self.assertIn("Path advisor is inactive", self.context(engine, "app/analytics/test.py", fixture_hook))

    def test_retired_optional_rule_has_no_active_consumers(self):
        self.assertFalse((ROOT / ".cursor/rules/vibe-tools.mdc").exists())
        active_docs = [
            ROOT / "scripts/harness_check.ps1",
            ROOT / "docs/harness/ai-rules-compatibility.md",
            ROOT / "docs/harness/doc-gardening.md",
            ROOT / "docs/harness/source-baseline-manifest.md",
        ]
        for path in active_docs:
            with self.subTest(path=str(path)):
                self.assertNotIn("vibe-tools.mdc", path.read_text(encoding="utf-8-sig"))

    def test_complete_harness(self):
        for engine in ENGINES:
            with self.subTest(engine=engine):
                # "passed with skips" (e.g. no Codex CLI on CI runners) is a pass by design: exit 0.
                self.assertRegex(
                    self.run_script(engine, ROOT / "scripts/harness_check.ps1"),
                    r"Harness check passed(\.| with skips:)",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
