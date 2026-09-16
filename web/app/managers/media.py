def with_media(row: dict, *path_fields: str) -> dict:
    view = dict(row)
    for field in path_fields:
        rel = row.get(field)
        if isinstance(rel, str) and rel:
            view[f"{field}_url"] = f"/api/media/{rel}"
    return view
