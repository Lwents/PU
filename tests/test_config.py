from pathlib import Path
import sys
import tempfile
import unittest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pubg_control.config import AppSettings, SettingsManager


class ConfigTests(unittest.TestCase):
    def test_default_settings(self):
        settings = AppSettings()
        self.assertEqual(settings.console, "")
        self.assertEqual(settings.index, 0)
        self.assertEqual(settings.version, "Tự nhận diện")

    def test_persistence_save_load(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "test_settings.json"
            mgr = SettingsManager(temp_file)
            self.assertTrue(mgr.save(console="C:\\fake\\ldconsole.exe", index=2, version="PUBG Mobile VNG"))

            reloaded = SettingsManager(temp_file)
            self.assertEqual(reloaded.current.console, "C:\\fake\\ldconsole.exe")
            self.assertEqual(reloaded.current.index, 2)
            self.assertEqual(reloaded.current.version, "PUBG Mobile VNG")


if __name__ == "__main__":
    unittest.main()
