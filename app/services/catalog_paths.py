from pathlib import Path

from app.models import Book, Catalog


class PathOutsideCatalogError(ValueError):
    pass


def catalog_root(catalog: Catalog) -> Path:
    try:
        return Path(catalog.root_path).resolve()
    except (OSError, RuntimeError) as exc:
        raise PathOutsideCatalogError(f"Cannot resolve catalog {catalog.name!r} root: {exc}") from exc


def relative_file_path(catalog: Catalog, file_path: Path) -> str:
    try:
        return file_path.resolve().relative_to(catalog_root(catalog)).as_posix()
    except ValueError:
        raise PathOutsideCatalogError(f"File is outside catalog {catalog.name!r}: {file_path}") from None


def resolve_book_file(book: Book) -> Path:
    if not book.file_path:
        raise FileNotFoundError("Book has no file path")
    relative = Path(book.file_path)
    if relative.is_absolute():
        raise PathOutsideCatalogError("Stored book path must be relative to its catalog")
    root = catalog_root(book.catalog)
    try:
        candidate = (root / relative).resolve()
    except (OSError, RuntimeError) as exc:
        raise PathOutsideCatalogError(f"Cannot resolve stored path {book.file_path!r}: {exc}") from exc
    try:
        candidate.relative_to(root)
    except ValueError:
        raise PathOutsideCatalogError(f"File is outside catalog {book.catalog.name!r}: {book.file_path}") from None
    return candidate
