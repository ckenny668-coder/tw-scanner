import pandas as pd

import momentum_scanner as ms
import tw_scanner as tw

HTML = """<table class=h4 align=center>
<tr align=center><td>有價證券代號及名稱</td><td>國際證券辨識號碼(ISIN Code)</td><td>上市日</td><td>市場別</td><td>產業別</td><td>CFICode</td><td>備註</td></tr>
<tr><td colspan=7><B> 股票 <B></td></tr>
<tr><td>1101　台灣水泥</td><td>TW0001101004</td><td>1962/02/09</td><td>上市</td><td>水泥工業</td><td>ESVUFR</td><td></td></tr>
<tr><td>2330　台積電</td><td>TW0002330008</td><td>1994/09/05</td><td>上市</td><td>半導體業</td><td>ESVUFR</td><td></td></tr>
<tr><td>6213　聯茂</td><td>TW0006213003</td><td>2001/01/01</td><td>上市</td><td>電子零組件業</td><td>ESVUFR</td><td></td></tr>
<tr><td>2002A　中鋼特</td><td>TW00002002A1</td><td>2000/01/01</td><td>上市</td><td>鋼鐵工業</td><td>EPNRAR</td><td></td></tr>
<tr><td colspan=7><B> ETF <B></td></tr>
<tr><td>0050　元大台灣50</td><td>TW0000050004</td><td>2003/06/30</td><td>上市</td><td></td><td>CEOGEU</td><td></td></tr>
<tr><td colspan=7><B> 股票 <B></td></tr>
<tr><td>3105　穩懋</td><td>TW0003105003</td><td>2010/01/01</td><td>上櫃</td><td>半導體業</td><td>ESVUFR</td><td></td></tr>
</table>"""


def test_parse_keeps_only_4digit_common_stocks_with_suffix():
    u = tw.parse_isin_html(HTML, "TW")
    assert list(u.index) == ["1101.TW", "2330.TW", "6213.TW", "3105.TW"]   # 排除 ETF 與 5 碼特別股
    assert u.loc["2330.TW", "name"] == "台積電"
    assert u.loc["2330.TW", "industry"] == "半導體業"
    assert u.loc["3105.TW", "code"] == "3105"


def test_otc_suffix():
    assert list(tw.parse_isin_html(HTML, "TWO").index)[0] == "1101.TWO"


def test_themes_override_only_listed_codes(tmp_path):
    f = tmp_path / "themes.csv"
    f.write_text("code,theme\n6213,CCL銅箔基板\n2330.TW,先進製程\n", encoding="utf-8")
    u = tw.apply_themes(tw.parse_isin_html(HTML, "TW"), str(f))
    assert u.loc["6213.TW", "industry"] == "CCL銅箔基板"
    assert u.loc["2330.TW", "industry"] == "先進製程"          # 允許帶 .TW 的代號
    assert u.loc["1101.TW", "industry"] == "水泥工業"          # 沒列到的維持原產業別
    assert u.loc["6213.TW", "sector"] == "電子零組件業"        # sector 不變


def test_missing_themes_file_is_fine():
    u = tw.parse_isin_html(HTML, "TW")
    pd.testing.assert_frame_equal(tw.apply_themes(u, "no_such_file.csv"), u)


def test_tw_params_use_twd_turnover():
    assert tw.TW_PARAMS.min_dollar_vol == 1e8 and tw.TW_PARAMS.min_price == 10.0
    assert tw.TW_PARAMS.atr_ratio_max == ms.Params().atr_ratio_max   # 選股邏輯與美股一致
