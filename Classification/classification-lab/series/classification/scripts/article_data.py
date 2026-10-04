"""Tokens for the article templates. Every number or table in a rendered article comes through here.

    @@v:file.csv|model=LightGBM|column|.3f@@                one cell of a CSV (filter columns as key=value, then the column, then a format)
    @@j:file.json|path.to.value|.1%@@                        one value of a JSON file
    @@table:file.csv|cols=a,b|rename=a:A,b:B|fmt=a:.3f;b:,.0f|where=model!=Prior|sort=a|desc|head=10@@   a Markdown table
    @@text:file.txt@@                                       a text artifact (for example a printed tree)
The format spec is a Python format spec, for example .3f  ,.0f  .1%  d
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _csv(name: str) -> pd.DataFrame:
    return pd.read_csv(ART / name)


def _fmt(x, spec: str) -> str:
    if isinstance(x, (bool, np.bool_)):
        return "yes" if x else "no"
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    if spec in ("", "s"):
        return str(x)
    if spec == "d":
        return f"{int(round(float(x))):,}"
    return format(float(x), spec) if not isinstance(x, str) else x


def v(file: str, *args: str) -> str:
    filters = [a for a in args if "=" in a]
    rest = [a for a in args if "=" not in a]
    col, spec = rest[0], (rest[1] if len(rest) > 1 else "")
    df = _csv(file)
    for f in filters:
        k, val = f.split("=", 1)
        df = df[df[k].astype(str) == val]
    if len(df) != 1:
        raise ValueError(f"@@v:{file}|{args}@@ matched {len(df)} rows")
    return _fmt(df.iloc[0][col], spec)


def j(file: str, path: str, spec: str = "") -> str:
    obj = json.loads((ART / file).read_text(encoding="utf-8"))
    for part in path.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return _fmt(obj, spec)


def table(file: str, *args: str) -> str:
    df = _csv(file) if file.endswith(".csv") else pd.DataFrame(json.loads((ART / file).read_text(encoding="utf-8")))
    opts = {}
    flags = set()
    for a in args:
        if "=" in a and not a.startswith("where="):
            k, val = a.split("=", 1)
            opts[k] = val
        elif a.startswith("where="):
            opts.setdefault("where", []).append(a[6:])
        else:
            flags.add(a)
    for w in opts.get("where", []):
        if "~" in w:                                         # col~a;b;c keeps rows whose value is one of a, b, c
            k, vals = w.split("~", 1)
            df = df[df[k].astype(str).isin(vals.split(";"))]
            continue
        for op in ("!=", "=="):
            if op in w:
                k, val = w.split(op, 1)
                m = df[k].astype(str) == val
                df = df[m] if op == "==" else df[~m]
                break
        else:
            k, val = w.split("=", 1)
            df = df[df[k].astype(str) == val]
    if "pivot" in opts:                                    # pivot=index:columns:values, keeping first-appearance order
        idx, colm, val = opts["pivot"].split(":")
        order = list(dict.fromkeys(df[idx]))
        corder = list(dict.fromkeys(df[colm]))
        df = df.pivot(index=idx, columns=colm, values=val).reindex(order)[corder].reset_index()
        df.columns = [str(c) for c in df.columns]
    if "sort" in opts:
        df = df.sort_values(opts["sort"], ascending="desc" not in flags)
    if "head" in opts:
        df = df.head(int(opts["head"]))
    cols = opts.get("cols", ",".join(df.columns)).split(",")
    fmts = dict(p.split(":", 1) for p in opts.get("fmt", "").split(";") if p)
    rename = dict(p.split(":", 1) for p in opts.get("rename", "").split(",") if p)
    header = [rename.get(c, c) for c in cols]
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(_fmt(row[c], fmts.get(c, ".3f" if isinstance(row[c], (float, np.floating)) else "")) for c in cols) + " |")
    return "\n".join(lines)


def text(file: str) -> str:
    return (ART / file).read_text(encoding="utf-8").rstrip()


TOKENS = {"v": v, "j": j, "table": table, "text": text}
