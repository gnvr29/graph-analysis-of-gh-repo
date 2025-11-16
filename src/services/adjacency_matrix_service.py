import html
import pandas as pd


def df_to_svg(df: pd.DataFrame, cell_w: int = 120, cell_h: int = 26) -> str:
    """Render a small, readable SVG table from a square DataFrame."""
    cols = list(df.columns)
    rows = list(df.index)
    ncols = len(cols)
    nrows = len(rows)
    width = cell_w * (ncols + 1)
    height = cell_h * (nrows + 1)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    parts.append('<style>text{font-family: Arial, Helvetica, sans-serif; font-size:12px}</style>')

    for j, header in enumerate([""] + cols):
        x = j * cell_w
        parts.append(f'<rect x="{x}" y="0" width="{cell_w}" height="{cell_h}" fill="#f3f4f6" stroke="#d1d5db"/>')
        label = html.escape(str(header)) if header else ""
        parts.append(f'<text x="{x + cell_w/2}" y="{cell_h/2 + 5}" text-anchor="middle">{label}</text>')

    for i, row_name in enumerate(rows):
        y = (i + 1) * cell_h
        parts.append(f'<rect x="0" y="{y}" width="{cell_w}" height="{cell_h}" fill="#fbfbfb" stroke="#eee"/>')
        parts.append(f'<text x="{cell_w/2}" y="{y + cell_h/2 + 5}" text-anchor="middle">{html.escape(str(row_name))}</text>')
        for j, col in enumerate(cols):
            x = (j + 1) * cell_w
            val = df.iat[i, j]
            txt = "" if (pd.isna(val) or val == 0) else str(val)
            parts.append(f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" fill="#ffffff" stroke="#eee"/>')
            parts.append(f'<text x="{x + cell_w/2}" y="{y + cell_h/2 + 5}" text-anchor="middle">{html.escape(txt)}</text>')

    parts.append('</svg>')
    return "".join(parts)