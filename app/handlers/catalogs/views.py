from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from starlette import status
from starlette.responses import RedirectResponse

from app.handlers.dependencies import CatalogServiceDependency
from app.models import CatalogKind
from app.template_utils import templates

router = APIRouter()


def _context(catalog_service: CatalogServiceDependency, request: Request, *, editing=None, form=None, error=None):
    catalogs = catalog_service.list()
    rows = [
        {
            "catalog": catalog,
            "book_count": catalog_service.book_count(catalog.id),
            "available": Path(catalog.root_path).is_dir(),
        }
        for catalog in catalogs
    ]
    return {
        "request": request,
        "catalog_rows": rows,
        "editing": editing,
        "form": form,
        "error": error,
        "kinds": list(CatalogKind),
    }


def _redirect(request: Request, message: str) -> RedirectResponse:
    url = str(request.url_for("manage_catalogs").include_query_params(sync_msg=message))
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/settings/catalogs")
def manage_catalogs(request: Request, catalog_service: CatalogServiceDependency):
    return templates.TemplateResponse(request, "catalogs.html", _context(catalog_service, request))


@router.get("/settings/catalogs/{catalog_id}/edit")
def edit_catalog(request: Request, catalog_id: int, catalog_service: CatalogServiceDependency):
    catalog = catalog_service.get(catalog_id)
    if catalog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog not found")
    return templates.TemplateResponse(request, "catalogs.html", _context(catalog_service, request, editing=catalog))


@router.post("/settings/catalogs")
def create_catalog(  # noqa: PLR0913
    request: Request,
    catalog_service: CatalogServiceDependency,
    name: str = Form(...),
    root_path: str = Form(...),
    kind: str = Form(...),
    enabled: bool = Form(default=False),
):
    form = {"name": name, "root_path": root_path, "kind": kind, "enabled": enabled}
    try:
        with catalog_service.transaction():
            catalog_service.create(name=name, root_path=root_path, kind=kind, enabled=enabled)
    except ValueError as exc:
        return templates.TemplateResponse(request, 
            "catalogs.html",
            _context(catalog_service, request, form=form, error=str(exc)),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return _redirect(request, f"Catalog {name.strip()!r} created")


@router.post("/settings/catalogs/{catalog_id}")
def update_catalog(  # noqa: PLR0913
    request: Request,
    catalog_id: int,
    catalog_service: CatalogServiceDependency,
    name: str = Form(...),
    root_path: str = Form(...),
    kind: str = Form(...),
    enabled: bool = Form(default=False),
):
    catalog = catalog_service.get(catalog_id)
    if catalog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog not found")
    form = {"name": name, "root_path": root_path, "kind": kind, "enabled": enabled}
    try:
        with catalog_service.transaction():
            catalog_service.update(catalog, name=name, root_path=root_path, kind=kind, enabled=enabled)
    except ValueError as exc:
        return templates.TemplateResponse(request, 
            "catalogs.html",
            _context(catalog_service, request, editing=catalog, form=form, error=str(exc)),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return _redirect(request, f"Catalog {name.strip()!r} updated")


@router.post("/settings/catalogs/{catalog_id}/delete")
def delete_catalog(request: Request, catalog_id: int, catalog_service: CatalogServiceDependency):
    catalog = catalog_service.get(catalog_id)
    if catalog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog not found")
    try:
        with catalog_service.transaction():
            catalog_service.delete(catalog)
    except ValueError as exc:
        return templates.TemplateResponse(request, 
            "catalogs.html",
            _context(catalog_service, request, error=str(exc)),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return _redirect(request, f"Catalog {catalog.name!r} deleted")
