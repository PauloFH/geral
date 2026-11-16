"""scripts/import_base.py: a new base never changes a board already played (or today's)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import import_base  # noqa: E402


def test_new_base_is_written_only_after_the_calendar_is_frozen(tmp_path, monkeypatch) -> None:
    base = tmp_path / "base.json"
    base.write_text(json.dumps({"paises": {"Q77": "Uruguai"}, "jogadores": []}))
    seen: list[str] = []
    monkeypatch.setattr(import_base, "BASE", base)
    monkeypatch.setattr(
        import_base, "freeze_until_tomorrow", lambda: seen.append(base.read_text()) or 3
    )

    import_base.write_base({"paises": {}, "jogadores": [{"id": "Q1"}]})

    assert seen and '"Q1"' not in seen[0]  # frozen with the old base
    written = json.loads(base.read_text())
    assert written["jogadores"] == [{"id": "Q1"}]
    assert written["paises"] == {"Q77": "Uruguai"}  # countries kept for frozen boards
