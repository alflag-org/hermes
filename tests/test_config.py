from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hermes.config import load_config
from hermes.errors import ConfigError


class ConfigTest(unittest.TestCase):
    def test_load_config_allows_secret_environment_variable_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "hermes.yml"
            config.write_text(
                """
proxmox:
  endpoint: https://pve.example.internal:8006
  token_id_env: HERMES_PROXMOX_TOKEN_ID
  token_secret_env: HERMES_PROXMOX_TOKEN_SECRET
""".lstrip(),
                encoding="utf-8",
            )

            loaded = load_config(str(config))

            self.assertEqual(loaded["proxmox"]["token_secret_env"], "HERMES_PROXMOX_TOKEN_SECRET")

    def test_load_config_rejects_inline_secret_like_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "hermes.yml"
            config.write_text(
                """
proxmox:
  endpoint: https://pve.example.internal:8006
  token_secret: pasted-secret
""".lstrip(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ConfigError, "inline secret-like value"):
                load_config(str(config))


if __name__ == "__main__":
    unittest.main()
