import pyperclip
from bs4 import BeautifulSoup
from collections import Counter
import lxml

def parse_table_from_clipboard(target_title):
    """
    クリップボードからHTMLを取得し、指定されたテーブルタイトルに対応するテーブルを解析して、
    アイテム名とその個数を辞書で返す。

    :param target_title: 抽出対象のテーブルタイトル（例: "鉱石"）
    :return: {アイテム名: 個数} の辞書
    """
    # クリップボードからHTMLを取得
    html_content = pyperclip.paste()
    soup = BeautifulSoup(html_content, 'lxml')

    # テーブルタイトルを探す
    titles = soup.find_all('b')

    for title in titles:
        if title.parent.name == 'center' and title.text.strip() == f"-{target_title}-":
            # タイトルの次にあるテーブルを探す
            table = title.find_next('table')
            if not table:
                return {}

            rows = table.find_all('tr')
            if len(rows) < 2:  # ヘッダー行だけならスキップ
                return {}

            # 2列目のデータを取得（1行目はスキップ）
            items = [
                row.find_all('td')[1].text.strip()
                for row in rows[1:] if len(row.find_all('td')) > 1
            ]

            # アイテム数をカウント
            return dict(Counter(items))

    return {}  # 指定したタイトルが見つからなかった場合

# サンプルプログラム
if __name__ == "__main__":
    table_title = "鉱石"  # 取得したいテーブルのタイトル
    # table_title = "アクセサリー倉庫"  # 取得したいテーブルのタイトル
    # table_title = "防具倉庫"  # 取得したいテーブルのタイトル
    # table_title = "武器倉庫"  # 取得したいテーブルのタイトル
    item_counts = parse_table_from_clipboard(table_title)

    # 結果を出力
    all_item_num = 0
    if item_counts:
        print(f"--- {table_title} ---")
        for item, count in item_counts.items():
            print(f"{item}: {count}")
            all_item_num += count
    else:
        print(f"Table with title '{table_title}' not found or empty.")

    print(all_item_num)