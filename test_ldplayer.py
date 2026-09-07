import threading
import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from ldplayer import Instance, LDPlayer, find_console


class ImmediateCancel:
    def is_set(self):
        return False

    def wait(self, seconds):
        return False


class LaunchTests(unittest.TestCase):
    def client(self, packages="package:com.vng.pubgmobile", ready=True):
        client = object.__new__(LDPlayer)
        client.instances = lambda: [Instance(3, "Test", 123, ready)]
        client.calls = []
        def command(*args, **kwargs):
            client.calls.append(args)
            if args[0] == "adb":
                query = args[-1]
                if "sys.boot_completed" in query:
                    return "1"
                if "pm list packages" in query:
                    return packages
                if "pidof" in query:
                    return "4567"
            return ""
        client.command = command
        return client

    def test_auto_detect_and_launch_selected_instance(self):
        client = self.client()
        result = client.open(3, "", ImmediateCancel(), lambda _: None)
        self.assertEqual(result[0].index, 3)
        self.assertIn(("runapp", "--index", 3, "--packagename", "com.vng.pubgmobile"), client.calls)

    def test_missing_game_does_not_launch(self):
        client = self.client("package:com.android.settings")
        with self.assertRaisesRegex(RuntimeError, "Chưa tìm thấy"):
            client.open(3, "", ImmediateCancel(), lambda _: None)
        self.assertFalse(any(args[0] == "runapp" for args in client.calls))

    def test_multiple_games_require_selection(self):
        client = self.client("package:com.vng.pubgmobile\npackage:com.tencent.ig")
        with self.assertRaisesRegex(RuntimeError, "nhiều bản"):
            client.open(3, "", ImmediateCancel(), lambda _: None)

    def test_explicit_version_must_be_installed(self):
        client = self.client()
        with self.assertRaisesRegex(RuntimeError, "chưa được cài"):
            client.open(3, "com.tencent.ig", ImmediateCancel(), lambda _: None)

    def test_cancel_does_not_launch_game(self):
        client = self.client()
        cancel = threading.Event()
        cancel.set()
        self.assertIsNone(client.open(3, "", cancel, lambda _: None))
        self.assertEqual(client.calls, [])

    def test_missing_instance(self):
        with self.assertRaisesRegex(RuntimeError, "không tồn tại"):
            self.client().open(9, "", ImmediateCancel(), lambda _: None)

    def test_emulator_only_does_not_require_adb(self):
        client = self.client()
        result = client.open(3, "", ImmediateCancel(), lambda _: None, game=False)
        self.assertEqual(result[0].hwnd, 123)
        self.assertEqual(client.calls, [])

    def test_adb_unavailable_has_actionable_error(self):
        client = self.client()
        client.adb = lambda *args: "adb.exe: device 'emulator-5560' not found"
        with self.assertRaisesRegex(RuntimeError, "Open local connection"):
            client.open(3, "", ImmediateCancel(), lambda _: None)

    def test_parse_list2(self):
        client = object.__new__(LDPlayer)
        client.command = lambda *args: "0,LDPlayer,123,456,1,100,200,1280,720,240\n2,Second,0,0,0,-1,-1\ninvalid"
        self.assertEqual(client.instances(), [Instance(0, "LDPlayer", 123, True), Instance(2, "Second", 0, False)])

    def test_adb_probe_targets_selected_instance(self):
        client = object.__new__(LDPlayer)
        client.command = Mock(side_effect=["PU_ADB_CONNECTED", "Physical size: 1600x900"])
        self.assertEqual(client.connect_adb(7), "Physical size: 1600x900")
        self.assertEqual(client.command.call_args_list[0].args,
                         ("adb", "--index", 7, "--command", "shell echo PU_ADB_CONNECTED"))

    def test_adb_error_is_not_connected(self):
        client = object.__new__(LDPlayer)
        client.command = Mock(return_value="error: device offline")
        with self.assertRaisesRegex(RuntimeError, "Open local connection"):
            client.connect_adb(2)

    def test_stale_saved_path_falls_back_to_custom_install(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / "dnconsole.exe"
            executable.touch()
            with patch("ldplayer.installation_paths", return_value=[Path(folder) / "dnplayer.exe"]), patch("ldplayer.shutil.which", return_value=None):
                self.assertEqual(Path(find_console(str(Path(folder) / "old" / "ldconsole.exe"))), executable)

    def test_valid_saved_path_has_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / "ldconsole.exe"
            executable.touch()
            with patch("ldplayer.installation_paths") as discover:
                self.assertEqual(Path(find_console(str(executable))), executable)
                discover.assert_not_called()


if __name__ == "__main__":
    unittest.main()
