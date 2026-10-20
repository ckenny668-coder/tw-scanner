"""台股版：強勢股 + 整理轉強掃描（上市 + 上櫃）
邏輯與美股版完全相同，只換股票池與預設參數，掃描核心共用 momentum_scanner.py。

  python tw_scanner.py --out tw_watchlist.csv
  python tw_scanner.py --atr-max 0.95 --as-of 2026-10-19

自訂題材(建議)：在同一資料夾放 tw_themes.csv（欄位 code,theme），
同一題材的股票會被當成同一板塊，供「板塊共振」使用。證交所的產業別太粗
(例如 CCL、PCB、被動元件都是「電子零組件業」)，自訂題材比較貼近實際的族群。
"""
from __future__ import annotations

import io
import os
import re
from dataclasses import replace

import pandas as pd

import momentum_scanner as ms

# 台股預設：價格與成交金額都是新台幣。yfinance 的台股成交量單位是「股」，
# 所以 收盤價 × 成交量 = 成交金額(新台幣)。
TW_PARAMS = replace(ms.Params(), min_price=10.0, min_dollar_vol=1e8)   # 20 日均額 >= 1 億元

_UA = {"User-Agent": "Mozilla/5.0 (tw-momentum-scanner)"}
# strMode=2 上市、4 上櫃。證交所的 isin 網站在新版 Python 上 https 憑證常驗證失敗，
# 所以先試 http、再試 https（不會關閉憑證驗證）。
_ISIN = {"TW": 2, "TWO": 4}


def parse_isin_html(html: str, suffix: str) -> pd.DataFrame:
    """解析證交所 ISIN 表，只留「股票」區段中 4 碼數字代號的普通股。
    回傳 index=Yahoo 代號(2330.TW / 6488.TWO)，欄位 code, name, sector, industry。"""
    raw = pd.read_html(io.StringIO(html), header=None)[0].astype(str)
    hdr = raw.index[raw.iloc[:, 0].str.contains("有價證券代號及名稱")]
    if len(hdr) == 0:
        raise RuntimeError("找不到表頭『有價證券代號及名稱』，證交所版面可能改了")
    h = hdr[0]
    df = raw.iloc[h + 1:].copy()
    df.columns = list(raw.iloc[h].str.strip())
    rows, section = [], None
    for vals in df.itertuples(index=False):
        vals = list(vals)
        if len(set(vals)) == 1:                       # 合併儲存格：區段標題列，如「股票」「ETF」
            section = vals[0].strip()
            continue
        if section == "股票":
            rows.append(vals)
    body = pd.DataFrame(rows, columns=df.columns)
    parts = body["有價證券代號及名稱"].str.split("　", n=1, expand=True)
    body["code"] = parts[0].str.strip()
    body["name"] = parts[1].str.strip() if parts.shape[1] > 1 else ""
    body = body[body["code"].str.fullmatch(r"\d{4}")]
    ind = body["產業別"].replace({"nan": None}) if "產業別" in body.columns else None
    out = pd.DataFrame({"code": body["code"], "name": body["name"],
                        "sector": ind, "industry": ind})
    out.index = out["code"] + "." + suffix
    out.index.name = "ticker"
    return out


def load_tw_universe(themes_path: str = "tw_themes.csv") -> pd.DataFrame:
    import requests
    frames = []
    for suffix, mode in _ISIN.items():
        text, last_err = None, None
        for scheme in ("http", "https"):
            try:
                r = requests.get(f"{scheme}://isin.twse.com.tw/isin/C_public.jsp?strMode={mode}",
                                 headers=_UA, timeout=30)
                r.raise_for_status()
                text = r.content.decode("big5hkscs", errors="replace")
                break
            except Exception as e:                    # noqa: BLE001
                last_err = e
        if text is None:
            raise RuntimeError(f"無法取得{'上市' if suffix == 'TW' else '上櫃'}股票清單：{last_err}")
        frames.append(parse_isin_html(text, suffix))
    uni = pd.concat(frames)
    uni = uni[~uni.index.duplicated()]
    return apply_themes(uni, themes_path)


def apply_themes(uni: pd.DataFrame, path: str = "tw_themes.csv") -> pd.DataFrame:
    """若有 tw_themes.csv(欄位 code,theme)，把 industry 換成自訂題材；沒列到的維持證交所產業別。"""
    if not path or not os.path.exists(path):
        return uni
    t = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    t["code"] = t["code"].str.extract(r"(\d{4})", expand=False)
    m = t.dropna(subset=["code", "theme"]).drop_duplicates("code").set_index("code")["theme"]
    uni = uni.copy()
    themed = uni["code"].map(m)
    uni["industry"] = themed.fillna(uni["industry"])
    return uni


def main():
    ms.run_cli(load_tw_universe, TW_PARAMS, "台股 強勢股 + 整理轉強掃描")


if __name__ == "__main__":
    main()
