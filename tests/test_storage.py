import sys
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Ensure discord and optional CLI modules are mocked if not installed
for mod in ["discord", "discord.ext", "discord.ext.commands", "discord.ext.tasks", "colorama", "dotenv", "bs4"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import main


@pytest.fixture(autouse=True)
def isolate_environment(tmp_path, monkeypatch):
    """Isolate config.json and tool_cache.json to a temp directory for test runs."""
    temp_config = tmp_path / "config.json"
    temp_cache = tmp_path / "tool_cache.json"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "CONFIG_FILE", str(temp_config))

    yield tmp_path


def test_save_and_load_config_with_unicode(isolate_environment):
    """Verify that configuration persists and reloads correctly with UTF-8 characters."""
    main.CHANNEL_ID = 123456789
    main.OWNER_ID = 987654321
    main.LAST_POSTED_TITLE = "SuperTool 🛠️ — The Ultimate CLI 🚀"
    main.PING_ROLE_ID = 555666777

    main.saveConfig()

    config_path = Path(main.CONFIG_FILE)
    assert config_path.exists()

    # Raw disk read should deserialize with valid UTF-8
    raw_content = config_path.read_text(encoding="utf-8")
    loaded_dict = json.loads(raw_content)
    assert loaded_dict["last_posted_title"] == "SuperTool 🛠️ — The Ultimate CLI 🚀"

    # Reset globals in memory
    main.CHANNEL_ID = None
    main.OWNER_ID = None
    main.LAST_POSTED_TITLE = ""
    main.PING_ROLE_ID = None

    # Load from disk
    main.loadConfig()
    assert main.CHANNEL_ID == 123456789
    assert main.OWNER_ID == 987654321
    assert main.LAST_POSTED_TITLE == "SuperTool 🛠️ — The Ultimate CLI 🚀"
    assert main.PING_ROLE_ID == 555666777


def test_load_config_missing_file_graceful():
    """Verify that loadConfig handles missing files gracefully without raising."""
    main.CONFIG_FILE = "non_existent_config.json"
    main.loadConfig()  # Should not raise exception


def test_update_cache_adds_new_tools_and_deduplicates(isolate_environment):
    """Verify updateCache appends new tools with Unicode and excludes duplicates."""
    batch_1 = [
        {"title": "Bat 🦇", "description": "Cat clone with syntax highlighting", "url": "https://bat.dev"},
        {"title": "Ripgrep 🔍", "description": "Fast recursive regex searcher", "url": "https://ripgrep.dev"}
    ]

    main.updateCache(batch_1)

    cache_path = Path("tool_cache.json")
    assert cache_path.exists()

    with open("tool_cache.json", "r", encoding="utf-8") as f:
        cached = json.load(f)
    assert len(cached) == 2
    assert cached[0]["title"] == "Bat 🦇"
    assert cached[1]["title"] == "Ripgrep 🔍"

    # Add overlapping batch
    batch_2 = [
        {"title": "Ripgrep 🔍", "description": "Duplicate should be ignored"},
        {"title": "Eza 📂", "description": "Modern ls replacement"}
    ]

    main.updateCache(batch_2)

    with open("tool_cache.json", "r", encoding="utf-8") as f:
        updated = json.load(f)

    assert len(updated) == 3
    titles = [t["title"] for t in updated]
    assert titles == ["Bat 🦇", "Ripgrep 🔍", "Eza 📂"]


def test_update_cache_corrupt_file_recovery(isolate_environment):
    """Verify updateCache recovers gracefully if tool_cache.json is corrupted."""
    cache_path = Path("tool_cache.json")
    cache_path.write_text("{corrupt json", encoding="utf-8")

    fresh_batch = [{"title": "Fd ⚡", "description": "Simple find"}]
    main.updateCache(fresh_batch)

    with open("tool_cache.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["title"] == "Fd ⚡"
