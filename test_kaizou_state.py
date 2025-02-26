import os
from bs4 import BeautifulSoup
import pyperclip
import pyautogui
import time

import pickle
from lxml import html


class KaizouStatus:
    RECIPE = ["水", "白", "火", "白", "水", "白", "白", "邪", "白", "白"]

    def __init__(self, weapon_name):
        self.weapon_name = weapon_name  # 改造対象の武器名
        self.is_needed_done_check = False  # 改造の完了チェックが必要か
        self._recipe_index = 0  # レシピの現在位置

    def get_next_kouseki(self):
        """次の改造に使用する鉱石を取得（ループ）"""
        kouseki = self.RECIPE[self._recipe_index]
        return kouseki

    def check_done(self):
        """改造を一つ進める"""
        self._recipe_index = (self._recipe_index + 1) % len(self.RECIPE)  # インデックスをループ

    def save_to_pickle(self):
        """インスタンスをピックルに保存（武器名をファイル名に）"""
        filename = f"{self.weapon_name}.pkl"
        with open(filename, 'wb') as f:
            pickle.dump(self, f)

    @classmethod
    def load_from_pickle(cls, filename):
        """ピックルからインスタンスを読み込む"""
        with open(filename, 'rb') as f:
            return pickle.load(f)

    @classmethod
    def create_from_weapon_name(cls, weapon_name):
        """武器名からインスタンスを自動取得（存在すればロード、なければ新規作成）"""
        filename = f"{weapon_name}.pkl"
        if os.path.exists(filename):
            return cls.load_from_pickle(filename)
        else:
            return cls(weapon_name)

    def update_next_to_do(self):
        pyautogui.hotkey("ctrl", "u")
        time.sleep(2)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(2)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(2)
        pyautogui.hotkey("ctrl", "w")
        html_content = pyperclip.paste()
        position, attack_power = self.get_weapon_info(html_content, )


    @staticmethod
    def get_weapon_info(html_source, weapon_name):
        """
        指定されたHTMLコンテンツから、武器名を検索し、
        その位置（上から何番目か）と攻撃力を取得する関数。

        :param html_source: HTMLの文字列
        :param weapon_name: 探したい武器名
        :return: (武器の位置（1始まりのインデックス）, 攻撃力), 見つからない場合は (-1, None)
        """
        tree = html.fromstring(html_source)
        weapon_names = []
        weapon_attacks = []

        # 各ラジオボタンのあるセルを取得
        radio_cells = tree.xpath("//td[input[@type='radio']]")

        for cell in radio_cells:
            # 「名称」列はラジオボタンの次の td 要素
            name_td = cell.xpath("following-sibling::td[1]")
            attack_td = cell.xpath("following-sibling::td[2]")  # 攻撃力の列

            if name_td and name_td[0].text is not None:
                weapon_names.append(name_td[0].text.strip())
                attack = attack_td[0].text.strip() if attack_td and attack_td[0].text is not None else None
                weapon_attacks.append(attack)
            else:
                weapon_names.append("-")
                weapon_attacks.append(None)

        # 指定された武器のインデックスを取得（見つかった場合は 1始まりのインデックスに変換）
        try:
            index = weapon_names.index(weapon_name)
            position = index  # 1-based index
            attack_power = float(weapon_attacks[index])
        except ValueError:
            position = None
            attack_power = None

        return position, attack_power

    @staticmethod
    def get_kouseki_position(html_source, kouseki_name):
        soup = BeautifulSoup(html_source, 'lxml')
    
        # 全てのテーブルを取得
        tables = soup.find_all('table')
        if len(tables) < 2:
            return f"'{kouseki_name}' not found."
    
        # 鉱石リストのテーブルを取得
        kouseki_table = tables[2]  # 2番目のテーブルが鉱石リストと仮定
        rows = kouseki_table.find_all('tr')
    
        kousekis = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 1 and not cols[1].find('input'):  # アイテム名が存在する列を抽出
                name = cols[1].text.strip()
                if name and name != "-":
                    kousekis.append(name)
    
        try:
            position = kousekis.index(kouseki_name)
            return position
        except ValueError:
            return None


html_content = pyperclip.paste()
print(KaizouStatus.get_weapon_info(html_content, "ヴール"))
print(KaizouStatus.get_kouseki_position(html_content, "邪のオシダン"))

# 使用例
weapon = "伝説の剣"

# すでにあるならロード、なければ新規作成
kaizou = KaizouStatus.create_from_weapon_name(weapon)

# 改造進行
kaizou.check_done()

# 保存
kaizou.save_to_pickle()

# 再読み込みテスト
loaded_kaizou = KaizouStatus.create_from_weapon_name(weapon)
print(loaded_kaizou.get_next_kouseki())
kaizou.save_to_pickle()
