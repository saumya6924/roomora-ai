import csv
import io
from collections.abc import Iterable

from fastapi import Response


def csv_response(filename: str, header: list[str], rows: Iterable[Iterable]) -> Response:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(header)
    for row in rows:
        # Cells starting with = + - @ are formulas in Excel; prefix them so exported text stays text.
        writer.writerow(["'" + c if isinstance(c, str) and c[:1] in "=+-@" else c for c in row])
    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
