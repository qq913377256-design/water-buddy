import tempfile
import unittest
from pathlib import Path

from water_buddy import config
from water_buddy.config import AppState, DrinkEntry, Settings, load_state, save_state, total_today_ml


class ConfigTests(unittest.TestCase):
    def test_entries_are_isolated_by_day(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_app_dir = config.APP_DIR
            original_state_path = config.STATE_PATH
            config.APP_DIR = Path(temp_dir)
            config.STATE_PATH = Path(temp_dir) / "state.json"
            try:
                yesterday = AppState(settings=Settings(), entries=[DrinkEntry(amount_ml=250, created_at="2026-07-06T09:00:00")])
                save_state(yesterday, "2026-07-06")

                today = load_state("2026-07-07")
                self.assertEqual(total_today_ml(today), 0)

                today.entries.append(DrinkEntry(amount_ml=150, created_at="2026-07-07T09:00:00"))
                save_state(today, "2026-07-07")

                self.assertEqual(total_today_ml(load_state("2026-07-06")), 250)
                self.assertEqual(total_today_ml(load_state("2026-07-07")), 150)
            finally:
                config.APP_DIR = original_app_dir
                config.STATE_PATH = original_state_path


if __name__ == "__main__":
    unittest.main()
