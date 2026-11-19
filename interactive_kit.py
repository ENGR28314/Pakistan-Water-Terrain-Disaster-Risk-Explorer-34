"""
interactive_kit.py
Reusable interactivity for every data table in the dashboard:
  explore(df, key)  ->  search box, column filters, numeric range filters, sort,
                        filtered table, CSV download and a one-click chart builder.
Uses only widgets available in older Streamlit releases (no `key=` on
st.*_chart; keys are passed only to widgets and st.plotly_chart).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
import plotly.express as px


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c) for c in df.columns]
    return df.reset_index(drop=True)


def explore(df: pd.DataFrame, key: str, title: str = "🔍 Search, filter, sort & chart this table",
            chart: bool = True, expanded: bool = False):
    """Render df with interactive controls. Returns the filtered DataFrame."""
    if df is None or len(df) == 0:
        st.dataframe(df, use_container_width=True, hide_index=True)
        return df
    df = _clean(df)
    out = df

    with st.expander(title, expanded=expanded):
        q = st.text_input("Search (matches any column)", value="", key=f"{key}_q")
        if q.strip():
            needle = q.strip().lower()
            mask = out.astype(str).apply(lambda col: col.str.lower().str.contains(needle, regex=False)).any(axis=1)
            out = out[mask]

        cat_cols = [c for c in df.columns
                    if not pd.api.types.is_numeric_dtype(df[c]) and 2 <= df[c].astype(str).nunique() <= 15]
        if cat_cols:
            pick = st.multiselect("Filter by column", cat_cols, default=[], key=f"{key}_fc")
            for c in pick:
                opts = sorted(df[c].astype(str).unique())
                sel = st.multiselect(f"{c} is…", opts, default=opts, key=f"{key}_f_{c}")
                out = out[out[c].astype(str).isin(sel)]

        num_cols = [c for c in df.columns
                    if pd.api.types.is_numeric_dtype(df[c]) and df[c].nunique() > 1
                    and c.lower() not in ("latitude", "longitude")]
        if num_cols:
            npick = st.multiselect("Numeric range filter", num_cols, default=[], key=f"{key}_nc")
            for c in npick:
                lo, hi = float(df[c].min()), float(df[c].max())
                r = st.slider(f"{c} range", lo, hi, (lo, hi), key=f"{key}_r_{c}")
                out = out[(out[c] >= r[0]) & (out[c] <= r[1])]

        c1, c2 = st.columns(2)
        with c1:
            sort_col = st.selectbox("Sort by", ["(original order)"] + list(df.columns), key=f"{key}_s")
        with c2:
            desc = st.checkbox("Descending", value=False, key=f"{key}_d")
        if sort_col != "(original order)":
            out = out.sort_values(sort_col, ascending=not desc, kind="stable")

        st.caption(f"Showing {len(out)} of {len(df)} rows.")

    st.dataframe(out, use_container_width=True, hide_index=True)

    if len(out):
        st.download_button("⬇️ Download these rows (CSV)", out.to_csv(index=False).encode("utf-8"),
                           file_name=f"{key}.csv", mime="text/csv", key=f"{key}_dl")

    if chart and len(out) >= 2:
        with st.expander("📊 Chart this table"):
            num_cols_o = [c for c in out.columns if pd.api.types.is_numeric_dtype(out[c])
                          and c.lower() not in ("latitude", "longitude")]
            label_cols = [c for c in out.columns if c not in num_cols_o]
            kind = st.selectbox("Chart type", ["Bar", "Line", "Scatter", "Pie", "Histogram"], key=f"{key}_ct")
            if not num_cols_o:
                st.info("This table has no numeric columns to chart. Try the search/filter tools above.")
            else:
                try:
                    if kind == "Histogram":
                        y = st.selectbox("Column", num_cols_o, key=f"{key}_hy")
                        fig = px.histogram(out, x=y)
                    elif kind == "Scatter" and len(num_cols_o) >= 2:
                        x = st.selectbox("X (numeric)", num_cols_o, key=f"{key}_sx")
                        y = st.selectbox("Y (numeric)", num_cols_o, index=1, key=f"{key}_sy")
                        fig = px.scatter(out, x=x, y=y,
                                         hover_name=label_cols[0] if label_cols else None)
                    else:
                        x = st.selectbox("Label (X)", label_cols or list(out.columns), key=f"{key}_x")
                        y = st.selectbox("Value (Y)", num_cols_o, key=f"{key}_y")
                        if kind == "Pie":
                            fig = px.pie(out, names=x, values=y)
                        elif kind == "Line":
                            fig = px.line(out, x=x, y=y, markers=True)
                        elif kind == "Scatter":
                            fig = px.scatter(out, x=x, y=y)
                        else:
                            fig = px.bar(out, x=x, y=y)
                    st.plotly_chart(fig, use_container_width=True, key=f"{key}_fig")
                except Exception as e:  # never break the page over an optional chart
                    st.info(f"Could not draw that chart for this selection ({type(e).__name__}).")
    return out
