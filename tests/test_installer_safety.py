"""Non-mutating installer preflight checks (stdlib only)."""
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install" / "install_termux.sh"


class TermuxInstallerSafetyTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("bash"), "Bash not available")
    def test_bash_syntax(self):
        result = subprocess.run(["bash", "-n", str(INSTALLER)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("bash"), "Bash not available")
    def test_default_is_read_only_from_foreign_cwd(self):
        with tempfile.TemporaryDirectory(prefix="mimo installer spaces ") as directory:
            foreign = pathlib.Path(directory)
            before_venv = (ROOT / ".venv").exists()
            before_logs = (ROOT / "logs").exists()
            result = subprocess.run(["bash", str(INSTALLER)], cwd=foreign,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(ROOT), result.stdout)
            self.assertIn("sin cambios", result.stdout)
            self.assertFalse((foreign / ".venv").exists())
            self.assertFalse((foreign / "logs").exists())
            self.assertEqual((ROOT / ".venv").exists(), before_venv)
            self.assertEqual((ROOT / "logs").exists(), before_logs)

    @unittest.skipUnless(shutil.which("bash"), "Bash not available")
    def test_explicit_dry_run_and_invalid_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            for arguments, expected in [(["--dry-run"], 0), (["--typo"], 2),
                                        (["--execute", "--dry-run"], 2)]:
                result = subprocess.run(["bash", str(INSTALLER), *arguments], cwd=directory,
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, expected, result.stderr)
            self.assertFalse((pathlib.Path(directory) / ".venv").exists())

    def test_powershell_preview_contract_is_declared(self):
        # Static contract check only; PS5/7 runtime still requires Windows/PowerShell.
        script = (ROOT / "install" / "install.ps1").read_text(encoding="utf-8")
        self.assertIn("[switch]$Execute", script)
        self.assertIn("if (-not $Execute)", script)
        self.assertIn("Join-Path $PSScriptRoot '..'", script)
        self.assertIn("& $VenvPython -m pip install", script)
        self.assertNotIn("Activate.ps1", script)
        self.assertNotIn("ExecutionPolicy Bypass", script)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell 7 not available")
    def test_powershell_preview_runtime(self):
        with tempfile.TemporaryDirectory(prefix="mimo ps spaces ") as directory:
            result = subprocess.run(["pwsh", "-NoProfile", "-File",
                                     str(ROOT / "install" / "install.ps1")],
                                    cwd=directory, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("sin cambios", result.stdout)
            self.assertFalse((pathlib.Path(directory) / ".venv").exists())


if __name__ == "__main__":
    unittest.main()
