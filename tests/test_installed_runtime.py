"""Upgrade-safe paths and loopback model connectivity for the installed edition."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from llm.ollama_worker import OllamaWorker
from runtime_paths import user_root, wake_model_dir, wake_model_ready
from scripts.install_kws_model import REQUIRED_FILES


class InstalledRuntimeTests(unittest.TestCase):
    def test_frozen_state_lives_outside_install_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(sys, "frozen", True, create=True):
                with patch.dict(os.environ, {"LOCALAPPDATA": temporary}):
                    expected = Path(temporary) / "PersonalJarvis"
                    self.assertEqual(user_root(), expected)
                    self.assertFalse(wake_model_ready())
                    wake_model_dir().mkdir(parents=True)
                    for name in REQUIRED_FILES:
                        (wake_model_dir() / name).write_bytes(b"model fixture")
                    self.assertTrue(wake_model_ready())

    def test_local_ollama_connection_bypasses_system_proxy(self):
        response = SimpleNamespace(models=[SimpleNamespace(model="qwen3.5:0.8b")])
        with patch("llm.ollama_worker.ollama.Client") as client_factory:
            client_factory.return_value.list.return_value = response
            worker = OllamaWorker("你好")
            worker._ensure_server()
            self.assertFalse(client_factory.call_args.kwargs["trust_env"])


if __name__ == "__main__":
    unittest.main()
