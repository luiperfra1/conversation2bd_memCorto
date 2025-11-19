# utils/make_sqlite_report.py
from __future__ import annotations
import argparse
import os
import sqlite3
from typing import Any, List, Tuple

TRUNC = 300  # para acortar celdas largas

def _truncate(val: Any, maxlen: int = TRUNC) -> str:
    s = "" if val is None else str(val)
    return s if len(s) <= maxlen else s[: maxlen - 1] + "…"

def _as_table(headers: List[str], rows: List[Tuple[Any, ...]], maxw: int = 600) -> str:
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(str(cell)))
    widths = [min(w, maxw // max(1, len(headers))) for w in widths]

    def fmt_row(cells):
        parts = []
        for i, cell in enumerate(cells):
            cell = _truncate("" if cell is None else str(cell), widths[i])
            parts.append(cell.ljust(widths[i]))
        return " | ".join(parts)

    sep = "-+-".join("-" * w for w in widths)
    out = [fmt_row(headers), sep]
    out += [fmt_row(r) for r in rows]
    return "\n".join(out)

def make_content_only_report(sqlite_path: str, out_path: str, sample_limit: int) -> None:
    conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    # Tablas de usuario
    cur = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    tables = [r[0] for r in cur.fetchall()]

    lines: List[str] = []
    for tname in tables:
        # Nº de filas
        try:
            nrows = conn.execute(f"SELECT COUNT(*) FROM '{tname}'").fetchone()[0]
        except sqlite3.Error:
            nrows = 0  # por si es tabla virtual rara

        if nrows == 0:
            continue  # saltar tablas vacías

        lines.append(f"Tabla: {tname}")
        lines.append(f"Filas: {nrows}")

        # Muestra
        sample = conn.execute(f"SELECT * FROM '{tname}' LIMIT {sample_limit}").fetchall()
        if sample:
            headers = sample[0].keys()
            rows = [tuple(r[h] for h in headers) for r in sample]
            lines.append(f"\nMuestra (hasta {sample_limit} filas):")
            lines.append(_as_table(list(headers), rows))
        lines.append("")  # línea en blanco entre tablas

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Reporte generado: {out_path}")

def main():
    p = argparse.ArgumentParser(description="Imprime solo el contenido (muestras) de tablas con filas.")
    p.add_argument("sqlite_path", help="Ruta al .sqlite/.db")
    p.add_argument("-o", "--out", default="sqlite_content.txt", help="TXT de salida")
    p.add_argument("--limit", type=int, default=15, help="Filas de muestra por tabla")
    args = p.parse_args()
    make_content_only_report(args.sqlite_path, args.out, args.limit)

if __name__ == "__main__":
    main()
