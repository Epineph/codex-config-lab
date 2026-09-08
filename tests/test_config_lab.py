"""Regression tests for writes, restoration, and config failure modes."""

from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "config_lab.py"
SPEC = importlib.util.spec_from_file_location("config_lab", MODULE)
lab = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lab)


class ConfigurationTests(unittest.TestCase):
  def test_observed_toml_errors(self):
    examples = (
      b'approval_policy="untrusted"\napproval_policy="on-request"',
      b'[sandbox_workspace_write]\n[sandbox_workspace_write]',
      b'[sandbox_workspace_write]\nnetwork_access=yes',
      (b'approval_policy={granular={request_permissions=true '
       b'skill_approval=true}}'),
    )
    for example in examples:
      with self.subTest(example=example):
        with self.assertRaises(tomllib.TOMLDecodeError):
          lab.inspect_config(example)

  def test_misnested_settings_and_invalid_effort(self):
    _, issues = lab.inspect_config(b'[auto_review]\nmodel="example"')
    self.assertTrue(any("not global" in issue for issue in issues))
    for value in (b'"max"', b'[]'):
      _, issues = lab.inspect_config(b'model_reasoning_effort=' + value)
      self.assertTrue(issues)

  def test_templates_and_model_escaping(self):
    for preset in ("recovery", "development"):
      config, issues = lab.inspect_config(lab.candidate(preset, "model-id"))
      self.assertEqual(config["model"], "model-id")
      self.assertFalse(issues)
    with self.assertRaises(ValueError):
      lab.candidate("recovery", 'bad"\nsandbox_mode="danger-full-access')

  def test_replace_restore_and_candidate_backup(self):
    with tempfile.TemporaryDirectory() as directory:
      target = Path(directory) / "config.toml"
      original = b'network_access = yes\n# preserve even broken original\n'
      target.write_bytes(original)
      candidate = lab.candidate("recovery", None)
      backup = lab.replace_with_backup(target, candidate)
      self.assertEqual(target.read_bytes(), candidate)
      self.assertEqual(target.stat().st_mode & 0o777, 0o600)
      with redirect_stdout(io.StringIO()):
        lab.restore(backup, False)
        self.assertEqual(target.read_bytes(), candidate)
        lab.restore(backup, True)
      self.assertEqual(target.read_bytes(), original)
      backups = list((target.parent / "config-lab-backups").iterdir())
      other = next(path for path in backups if path != backup)
      self.assertEqual((other / "config.toml").read_bytes(), candidate)

  def test_restore_original_absence(self):
    with tempfile.TemporaryDirectory() as directory:
      target = Path(directory) / "config.toml"
      backup = lab.replace_with_backup(target, b"# new\n")
      with redirect_stdout(io.StringIO()):
        lab.restore(backup, True)
      self.assertFalse(target.exists())

  def test_corrupt_backup_does_not_touch_target(self):
    with tempfile.TemporaryDirectory() as directory:
      target = Path(directory) / "config.toml"
      target.write_bytes(b"# original\n")
      backup = lab.replace_with_backup(target, b"# candidate\n")
      (backup / "config.toml").write_bytes(b"# corrupted\n")
      with self.assertRaises(ValueError):
        lab.restore(backup, True)
      self.assertEqual(target.read_bytes(), b"# candidate\n")

  def test_invalid_backup_manifest_does_not_touch_target(self):
    with tempfile.TemporaryDirectory() as directory:
      target = Path(directory) / "config.toml"
      target.write_bytes(b"# original\n")
      backup = lab.replace_with_backup(target, b"# candidate\n")
      (backup / "manifest.json").write_text("[]")
      with self.assertRaisesRegex(ValueError, "manifest"):
        lab.restore(backup, True)
      self.assertEqual(target.read_bytes(), b"# candidate\n")

  def test_symlinked_backup_refused(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      target = root / "config.toml"
      target.write_bytes(b"# original\n")
      backup = lab.replace_with_backup(target, b"# candidate\n")
      link = root / "linked-backup"
      link.symlink_to(backup, target_is_directory=True)
      with self.assertRaisesRegex(ValueError, "symlink"):
        lab.restore(link, True)
      self.assertEqual(target.read_bytes(), b"# candidate\n")

  def test_symlink_refused(self):
    with tempfile.TemporaryDirectory() as directory:
      original = Path(directory) / "original.toml"
      original.write_bytes(b"# original\n")
      link = Path(directory) / "config.toml"
      link.symlink_to(original)
      with self.assertRaises(ValueError):
        lab.replace_with_backup(link, b"# changed\n")
      self.assertEqual(original.read_bytes(), b"# original\n")

  def test_preview_has_no_filesystem_changes(self):
    with tempfile.TemporaryDirectory() as directory:
      target = Path(directory) / "missing" / "config.toml"
      argv = ["config_lab.py", "apply", "--target", str(target)]
      with patch("sys.argv", argv), redirect_stdout(io.StringIO()):
        self.assertEqual(lab.main(), 0)
      self.assertFalse(target.parent.exists())

  def test_lab_credentials_preserved_when_switching_presets(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      (root / "config").mkdir()
      for preset in ("recovery", "development"):
        source = lab.ROOT / "config" / f"{preset}.toml"
        (root / "config" / source.name).write_bytes(source.read_bytes())
      target = root / ".local-state" / "codex" / "config.toml"
      with patch.object(lab, "ROOT", root), redirect_stdout(io.StringIO()):
        with patch("sys.argv", ["config_lab.py", "init-lab"]):
          lab.main()
        with patch("sys.argv", ["config_lab.py", "init-lab"]):
          with self.assertRaises(ValueError):
            lab.main()
        argv = ["config_lab.py", "apply", "--preset", "development",
                "--target", str(target), "--write"]
        with patch("sys.argv", argv):
          lab.main()
      config = tomllib.loads(target.read_text())
      self.assertEqual(config["cli_auth_credentials_store"], "file")
      self.assertEqual(config["model_reasoning_effort"], "xhigh")


if __name__ == "__main__":
  unittest.main()
