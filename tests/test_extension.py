import json
from pathlib import Path


def test_manifest_v3_and_required_files():
    root = Path("extension")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 3
    assert {"activeTab", "scripting"} <= set(manifest["permissions"])
    assert manifest["background"]["service_worker"] == "background.js"
    for file in ("content.js", "background.js", "popup.html", "popup.js", "styles.css"):
        assert (root / file).is_file()


def test_live_safety_features_present():
    content = Path("extension/content.js").read_text(encoding="utf-8")
    background = Path("extension/background.js").read_text(encoding="utf-8")
    popup = Path("extension/popup.js").read_text(encoding="utf-8")
    assert "MutationObserver" in content
    assert "crypto.randomUUID" in content
    assert "resumeSubmission" in content
    assert "UNAUDITED" in background
    assert "setBadgeText" in background
    assert 'const API = "http://127.0.0.1:8000"' in background
    assert 'fetch("http://127.0.0.1:8000/health"' in popup
    assert 'url: "http://127.0.0.1:8000/"' in popup


def test_all_supported_ai_submit_selectors_present():
    manifest = json.loads(Path("extension/manifest.json").read_text(encoding="utf-8"))
    content = Path("extension/content.js").read_text(encoding="utf-8")
    background = Path("extension/background.js").read_text(encoding="utf-8")
    matches = {match for script in manifest["content_scripts"] for match in script["matches"]}
    assert "https://chatgpt.com/*" in matches
    assert "https://chat.openai.com/*" in matches
    assert "https://claude.ai/*" in matches
    assert "https://gemini.google.com/*" in matches
    assert "https://copilot.microsoft.com/*" in matches
    assert "https://chat.deepseek.com/*" in matches
    assert "button[data-test-id*='send']" in content
    assert "div[contenteditable='true']" in content
    assert "[role='textbox']" in content
    assert 'eventRoot.addEventListener("paste"' in content
    assert 'eventRoot.addEventListener("drop"' in content
    assert 'eventRoot.addEventListener("change"' in content
    assert "failOpen: false" in background
    assert "auditFilesAndRelease" in content
    assert "INSPECTABLE_FILE_TYPES" in content
    assert "ADJUNTO_LOCAL" in content
