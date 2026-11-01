from pathlib import Path

from app.models import Catalog, CatalogKind
from app.repositories.data_store import DataStore


class CatalogService:
    def __init__(self, store: DataStore):
        self.store = store

    def transaction(self):
        return self.store.transaction()

    def list(self) -> list[Catalog]:
        return list(self.store.catalog_repo.list_all("name"))

    def get(self, catalog_id: int) -> Catalog | None:
        return self.store.catalog_repo.get_by_params(id=catalog_id)

    def book_count(self, catalog_id: int) -> int:
        return self.store.catalog_repo.count_books(catalog_id)

    def create(self, *, name: str, root_path: str, kind: str, enabled: bool) -> Catalog:
        values = self._validate(name=name, root_path=root_path, kind=kind, enabled=enabled)
        return self.store.catalog_repo.create(**values)

    def update(self, catalog: Catalog, *, name: str, root_path: str, kind: str, enabled: bool) -> Catalog:
        values = self._validate(name=name, root_path=root_path, kind=kind, enabled=enabled, exclude_id=catalog.id)
        root_changed = values["root_path"] != catalog.root_path
        if root_changed:
            self._validate_available(Path(values["root_path"]))
        for key, value in values.items():
            setattr(catalog, key, value)
        return catalog

    def delete(self, catalog: Catalog) -> None:
        if self.book_count(catalog.id):
            raise ValueError("Only an empty catalog can be deleted. Disable it instead.")
        self.store.session.delete(catalog)

    def _validate(
        self,
        *,
        name: str,
        root_path: str,
        kind: str,
        enabled: bool,
        exclude_id: int | None = None,
    ) -> dict:
        name = name.strip()
        if not name:
            raise ValueError("Catalog name is required.")
        if kind not in {item.value for item in CatalogKind}:
            raise ValueError("Unknown catalog type.")

        raw_path = Path(root_path.strip()).expanduser()
        if not raw_path.is_absolute():
            raise ValueError("Catalog path must be absolute (a path inside the container in Docker).")
        try:
            root = raw_path.resolve()
        except (OSError, RuntimeError) as exc:
            raise ValueError(f"Cannot resolve catalog path: {exc}") from exc

        if exclude_id is None:
            self._validate_available(root)

        for other in self.list():
            if other.id == exclude_id:
                continue
            try:
                other_root = Path(other.root_path).resolve()
            except (OSError, RuntimeError):
                continue
            if root == other_root:
                raise ValueError(f"This path is already used by catalog {other.name!r}.")
            if root in other_root.parents or other_root in root.parents:
                raise ValueError(f"Catalog paths must not overlap with {other.name!r} ({other.root_path}).")

        return {"name": name, "root_path": str(root), "kind": kind, "enabled": enabled}

    @staticmethod
    def _validate_available(root: Path) -> None:
        if not root.is_dir():
            raise ValueError(f"Catalog directory does not exist or is not accessible: {root}")
