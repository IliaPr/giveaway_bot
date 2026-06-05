import os
import unittest
from unittest.mock import patch

from config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_supports_database_url(self) -> None:
        env = {
            "BOT_TOKEN": "token",
            "REDIS_URL": "redis://localhost:6379/0",
            "DATABASE_URL": "postgres://user:pass@localhost:5432/dbname",
        }

        with patch.dict(os.environ, env, clear=True):
            config = load_config()

        self.assertEqual(
            config.database_dsn,
            "postgresql://user:pass@localhost:5432/dbname",
        )


if __name__ == "__main__":
    unittest.main()
