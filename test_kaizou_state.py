import pickle
import os


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
    def from_weapon_name(cls, weapon_name):
        """武器名からインスタンスを自動取得（存在すればロード、なければ新規作成）"""
        filename = f"{weapon_name}.pkl"
        if os.path.exists(filename):
            return cls.load_from_pickle(filename)
        else:
            return cls(weapon_name)


# 使用例
weapon = "伝説の剣"

# すでにあるならロード、なければ新規作成
kaizou = KaizouStatus.from_weapon_name(weapon)

# 改造進行
kaizou.check_done()
kaizou.check_done()

# 保存
kaizou.save_to_pickle()

# 再読み込みテスト
loaded_kaizou = KaizouStatus.from_weapon_name(weapon)
print(f"[{loaded_kaizou.weapon_name}] 改造履歴: {loaded_kaizou.kaizou_position}")