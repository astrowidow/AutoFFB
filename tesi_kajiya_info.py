from bs4 import BeautifulSoup
import pyperclip

from bs4 import BeautifulSoup


def find_weapon_position(html_content, weapon_name):
    from lxml import html

    html_content = """
    <table>
        <tr>
        <form action=shop.cgi method=post onSubmit=return check()>
        <th></th><th></th><th>名称</th><th>攻撃力</th><th>価格</th></tr>
        <tr><td rowspan=2 class=b1><IMG src=https://kroko.jp/image//mini_ded.gif>
            <td class=b1><input type=radio name=kaizo value=item2></td><td class=b1>ロケット花火</td><td align=right class=b1>1024</td><td align=right class=b1>25</td>
        </tr>
        <tr><td class=b1><input type=radio name=kaizo value=def2></td><td class=b1>-</td><td align=right class=b1>7.37869762948384e+23</td><td align=right class=b1>25,000,000,000</td></tr>
        <tr><td rowspan=2 class=b1><IMG src=https://kroko.jp/image//mini_mire_nia_hane.gif>
            <td class=b1><input type=radio name=kaizo value=item3></td><td class=b1>-</td><td align=right class=b1>0</td><td align=right class=b1>0</td>
        </tr>
        <tr><td class=b1><input type=radio name=kaizo value=def3></td><td class=b1>AT</td><td align=right class=b1>6.64613997892456e+39</td><td align=right class=b1>25,000,000,000</td></tr>
        <tr><td rowspan=2 class=b1><IMG src=https://kroko.jp/image//iton.gif>
            <td class=b1><input type=radio name=kaizo value=item4></td><td class=b1>-</td><td align=right class=b1>0</td><td align=right class=b1>0</td>
        </tr>
        <tr><td class=b1><input type=radio name=kaizo value=def4></td><td class=b1>ヴェール</td><td align=right class=b1>6.64613997892456e+39</td><td align=right class=b1>25,000,000,000</td></tr>
    </table>
    """

    # HTML解析
    tree = html.fromstring(html_content)

    # 「名称」列の要素をすべて取得
    weapon_names = [td.text.strip() if td.text else "" for td in tree.xpath("//td[3]")]

    # 結果の表示
    print(weapon_names)


def find_ore_position(html_content, ore_name):
    soup = BeautifulSoup(html_content, 'lxml')

    # 全てのテーブルを取得
    tables = soup.find_all('table')
    if len(tables) < 2:
        return f"'{ore_name}' not found."

    # 鉱石リストのテーブルを取得
    ore_table = tables[2]  # 2番目のテーブルが鉱石リストと仮定
    rows = ore_table.find_all('tr')

    ores = []
    for row in rows:
        cols = row.find_all('td')
        if len(cols) > 1 and not cols[1].find('input'):  # アイテム名が存在する列を抽出
            name = cols[1].text.strip()
            if name and name != "-":
                ores.append(name)

    try:
        position = ores.index(ore_name)
        return f"'{ore_name}' is at position {position}."
    except ValueError:
        return f"'{ore_name}' not found."


html_content = pyperclip.paste()
print(find_weapon_position(html_content, "ロケット花火"))
print(find_ore_position(html_content, "火のルビー"))
