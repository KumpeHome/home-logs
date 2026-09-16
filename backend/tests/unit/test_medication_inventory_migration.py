import importlib.util
from pathlib import Path


def _load_revision():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "003_medication_inventory.py"
    )
    spec = importlib.util.spec_from_file_location("rev_003_medication_inventory", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_downgrade_skips_tables_that_upgrade_would_have_skipped(monkeypatch) -> None:
    module = _load_revision()
    dropped: list[tuple[str, str]] = []

    class FakeInspect:
        def get_table_names(self) -> list[str]:
            return ["medications"]

        def get_columns(self, table: str) -> list[dict]:
            if table != "medications":
                raise AssertionError(f"should not inspect missing table {table}")
            return [{"name": "id"}, {"name": "quantity_on_hand"}, {"name": "pharmacy"}]

    monkeypatch.setattr(module.op, "get_bind", lambda: object())
    monkeypatch.setattr(
        module.op, "drop_column", lambda table, name: dropped.append((table, name))
    )
    monkeypatch.setattr(module, "inspect", lambda _bind: FakeInspect())

    module.downgrade()

    assert ("household_otc_medications", "quantity_on_hand") not in dropped
    assert ("medications", "quantity_on_hand") in dropped
    assert ("medications", "pharmacy") in dropped
    assert ("medications", "id") not in dropped


def test_downgrade_skips_inventory_columns_that_are_not_present(monkeypatch) -> None:
    module = _load_revision()
    dropped: list[tuple[str, str]] = []

    class FakeInspect:
        def get_table_names(self) -> list[str]:
            return ["medications", "household_otc_medications"]

        def get_columns(self, table: str) -> list[dict]:
            if table == "medications":
                return [{"name": "id"}, {"name": "quantity_on_hand"}]
            return [{"name": "id"}]

    monkeypatch.setattr(module.op, "get_bind", lambda: object())
    monkeypatch.setattr(
        module.op, "drop_column", lambda table, name: dropped.append((table, name))
    )
    monkeypatch.setattr(module, "inspect", lambda _bind: FakeInspect())

    module.downgrade()

    assert dropped == [("medications", "quantity_on_hand")]
