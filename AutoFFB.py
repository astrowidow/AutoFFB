import os
import sys
import time
import datetime
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pyautogui
import requests
import cv2
import numpy as np
import pyscreeze as pysc
import PIL as PIL  # pillowで検索


class IPManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IPManager, cls).__new__(cls)
        return cls._instance  # インスタンスを作るだけ（変数の初期化はしない）

    def __init__(self):
        if not hasattr(self, "initialized"):  # 初回だけ初期化
            self.initial_ip = self.get_public_ip()
            self.pc_name = os.environ.get("COMPUTERNAME", "unknown")
            self.log_dir = self.get_log_directory()
            self.initialized = True  # 2回目以降の `__init__` で再初期化しない

            if self.initial_ip:
                print(f"✅ 初期VPN IP: {self.initial_ip}")
            else:
                print("⚠️ 初回のIPアドレス取得に失敗しました。インターネット接続を確認してください。")

    def reset_ip(self):
        self.initial_ip = self.get_public_ip()

    @staticmethod
    def get_log_directory():
        base_doc_path = os.path.expanduser("~/Documents")
        if not os.path.exists(base_doc_path):
            base_doc_path = os.path.join(os.path.expanduser("~"), "OneDrive", "ドキュメント")
        log_dir = os.path.join(base_doc_path, "ffb", "ip")
        os.makedirs(log_dir, exist_ok=True)
        return log_dir

    @staticmethod
    def get_public_ip():
        try:
            options = Options()
            options.debugger_address = "127.0.0.1:9222"  # 既存のChromeセッションに接続

            # ✅ Pythonスクリプトと同じフォルダにある chromedriver を指定
            script_dir = os.path.dirname(os.path.abspath(__file__))
            driver_path = os.path.join(script_dir, "chromedriver.exe" if os.name == "nt" else "chromedriver")

            service = Service(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=options)

            # ✅ C# の `Navigate().GoToUrl()` と同じ動作
            driver.execute_script("window.location = 'https://api64.ipify.org';")

            # ✅ `<body>` のテキストを取得（即座に実行）
            element = driver.find_element(By.TAG_NAME, "body")
            ip = element.text.strip()

            # 🔥 既存の Chrome を閉じないように `driver.close()` を削除
            return ip

        except Exception as e:
            print(f"⚠️ Chrome経由でのIP取得エラー: {e}")
            return ""

    def wait_for_ip_recovery(self, max_wait_time=1800, target_stable_time=600, check_interval=30):
        elapsed_time = 0
        last_ip = ""
        stable_time = 0
        notifier = Notifier()

        while elapsed_time < max_wait_time:
            current_ip = self.get_public_ip()

            if not current_ip:
                print("⚠️ 現在のIPアドレス取得に失敗。再試行します...")
            elif current_ip == self.initial_ip:
                if elapsed_time > 0:
                    print("✅ IPアドレスが元に戻りました。通常処理を続行します。")
                    notifier.send_discord_message("✅ IPアドレスが元に戻りました。通常処理を続行します。")
                    self.log_ip_change(self.initial_ip, self.initial_ip, elapsed_time)
                return
            else:
                if current_ip != last_ip:
                    notifier.send_discord_message("⚠️ IPアドレスの変更が検知されました。IPアドレスが元に戻るか、変化後のIPで安定するのを確認できるまで待機します。")
                    last_ip = current_ip
                    stable_time = 0
                else:
                    stable_time += check_interval

                if stable_time >= target_stable_time:
                    print(f"⏳ 新しいIP {last_ip} をマスターとして採用 (維持時間: {stable_time}秒)")
                    notifier.send_discord_message(f"✅ 変更後のIPアドレス {last_ip} をマスターとして採用し、通常処理を続行します。")
                    self.log_ip_change(self.initial_ip, last_ip, elapsed_time)
                    self.initial_ip = last_ip  # 新しいIPをマスターにする
                    return
                else:
                    print(
                        f"⚠️ IP変化: {self.initial_ip} → {current_ip} (維持時間: {stable_time}s / 目標: {target_stable_time}s)")

            time.sleep(check_interval)
            elapsed_time += check_interval

        print("⚠️ 最大待機時間を超えました。処理を継続します。")
        notifier.send_discord_message(
            "🚨 IPアドレス変更後の待機においてタイムアウトが発生しました。")

    def log_ip_change(self, old_ip, new_ip, elapsed_time):
        """IP変更のログをドキュメントフォルダに保存する"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} | 旧IP: {old_ip} → 新IP: {new_ip} | 経過時間: {elapsed_time}秒\n"

        # ログファイルのパス
        counter = 1
        while True:
            log_file = os.path.join(self.log_dir, f"{counter:04d}_{self.pc_name}_ip_change.txt")
            if not os.path.exists(log_file):
                break
            counter += 1

        # ログを書き込み
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(log_entry)

        print(f"📄 IP変更ログを記録しました: {log_file}")


class JumpHandler:
    jump_used = False

    def __init__(self, jump_key, wait_key, time_after_key_down=20, time_after_confirmation_range=(5000, 10000),
                 offset_x=0, offset_y=0, react_keitai=True, enable_adaptive_wait=True, react_error=True):
        self.jump_key = jump_key
        self.wait_key = wait_key
        self.time_after_key_down = time_after_key_down
        self.time_after_confirmation_range = time_after_confirmation_range
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.react_keitai = react_keitai
        self.react_error = react_error
        self.enable_adaptive_wait = enable_adaptive_wait
        self.transition_timeout = 60
        self.ip_manager = IPManager()  # シングルトンを参照

    def jump_with_confirmation(self):
        time_after_confirmation = random.randint(*self.time_after_confirmation_range)  # 実行時に乱数適用
        reason = self.jump_with_confirmation_core(
            jump_key=self.jump_key, wait_key=self.wait_key,
            time_after_key_down=self.time_after_key_down,
            time_after_confirmation=time_after_confirmation,
            offset_x=self.offset_x, offset_y=self.offset_y,
            react_keitai=self.react_keitai, enable_adaptive_wait=self.enable_adaptive_wait,
            react_error=self.react_error
        )

        notifier = Notifier()
        if reason == "Timeout":
            notifier.send_discord_message("🚨 ページ遷移でタイムアウトが発生しました")

        if reason == "ErrorInterrupt":
            notifier.send_discord_message("⚠️ エラーページが表示されました。ステータス画面への遷移を試みます。")
            print(f"エラーが発生したため、ステータスに戻します。 (元の遷移 from:{self.jump_key} to:{self.wait_key})")
            reason_error = self.jump_with_confirmation_core(
                jump_key="to-status", wait_key="isStatus",
                time_after_key_down=100,
                time_after_confirmation=10000,
                react_keitai=self.react_keitai,
                react_error=False
            )
            if reason_error == "PageTransition":
                notifier.send_discord_message("✅ エラーページからステータス画面へ遷移に成功しました。")
            else:
                notifier.send_discord_message("🚨 エラーページからステータス画面へ遷移に失敗しました。。。")

        JumpHandler.jump_used = True

    def jump_with_confirmation_core(self, jump_key, wait_key, time_after_key_down, time_after_confirmation, offset_x=0,
                                    offset_y=0, react_keitai=True, enable_adaptive_wait=True, react_error=True):
        location = ImageRecognizer.locate_center(jump_key)
        if location:
            print(f"id: {jump_key}, x: {location[0]}, y: {location[1]}")
            self.ip_manager.wait_for_ip_recovery()

            target_x = location[0] + offset_x
            target_y = location[1] + offset_y
            pyautogui.click(target_x, target_y, duration=time_after_key_down / 1000)

            print(f"ページ遷移待ち処理開始 from:{jump_key} to:{wait_key}")
            elapsed_time, reason = self.wait_for_transition(
                wait_key=wait_key,
                react_keitai=react_keitai,
                react_error=react_error
            )
            print(f"ページ遷移処理完了: {elapsed_time} 秒, 終了理由: {reason}")

            final_wait_time = time_after_confirmation
            if enable_adaptive_wait:
                adaptive_wait_time = int(elapsed_time * 2000)
                final_wait_time = max(time_after_confirmation, adaptive_wait_time)
                print(
                    f"遷移後待機時間: {final_wait_time} msec (基準: {time_after_confirmation} msec, 応答ベース: {adaptive_wait_time} msec)")

            time.sleep(final_wait_time / 1000)
            return reason
        else:
            return "ButtonNotFound"

    def wait_for_transition(self, wait_key, react_keitai=True, react_error=True, waiting_interval=50):
        start_time = time.time()
        while time.time() - start_time < self.transition_timeout:
            if ImageRecognizer.locate_center(wait_key):
                return time.time() - start_time, "PageTransition"
            elif ImageRecognizer.locate_center("keitai"):
                if react_keitai:
                    return time.time() - start_time, "KeitaiInterrupt"
            elif ImageRecognizer.locate_center("error"):
                if react_error:
                    return time.time() - start_time, "ErrorInterrupt"
            time.sleep(waiting_interval / 1000)
        return self.transition_timeout, "Timeout"


class JumpManager:
    @staticmethod
    def jump_to_champ():
        JumpHandler("champ", "is-champ", time_after_confirmation_range=(3249, 4836)).jump_with_confirmation()

    @staticmethod
    def jump_to_bougu():
        JumpHandler("bougu-ya", "is-bougu-ya", time_after_confirmation_range=(2249, 2836)).jump_with_confirmation()

    @staticmethod
    def jump_to_challenge_character():
        JumpHandler("chara", "is-chara", time_after_confirmation_range=(549, 736)).jump_with_confirmation()

    @staticmethod
    def jump_to_status():
        JumpHandler("to-status", "isStatus", time_after_confirmation_range=(2249, 5236)).jump_with_confirmation()

    @staticmethod
    def jump_to_auction_from_status():
        JumpHandler("auc", "is-auc", time_after_confirmation_range=(2249, 3236)).jump_with_confirmation()

    @staticmethod
    def jump_to_auction_from_shuppin_result():
        JumpHandler("back-to-auc", "is-auc", time_after_confirmation_range=(2249, 3236)).jump_with_confirmation()

    @staticmethod
    def jump_to_shuppin_select():
        JumpHandler("go-to-shuppin", "is-shuppin", time_after_confirmation_range=(2249, 3236)).jump_with_confirmation()

    @staticmethod
    def jump_to_shuppin_result():
        JumpHandler("acu-shuppin", "shuppin-done", time_after_confirmation_range=(2249, 3236)).jump_with_confirmation()

    @staticmethod
    def jump_to_manomori():
        JumpHandler("go-to-manomori", "in-manomori", time_after_confirmation_range=(1549, 2336),
                    offset_x=83).jump_with_confirmation()

    @staticmethod
    def jump_to_saishu():
        JumpHandler("go-to-manomori", "go-to-last", time_after_confirmation_range=(1549, 2336)).jump_with_confirmation()
        JumpHandler("go-to-last", "go-to-last", time_after_confirmation_range=(1549, 2336)).jump_with_confirmation()
        JumpHandler("go-to-last", "in-last", time_after_confirmation_range=(1549, 2336),
                    offset_x=80).jump_with_confirmation()

    @staticmethod
    def jump_to_next_manomori():
        JumpManager.jump_to_next_makyo("in-manomori")

    @staticmethod
    def jump_to_next_saishu():
        JumpManager.jump_to_next_makyo("in-last")

    @staticmethod
    def jump_to_next_makyo(wait_key):
        jump_key = "manomori-win"
        if ImageRecognizer.locate_center(wait_key):
            time_after_confirmation = (18549, 26636)
        else:
            time_after_confirmation = (2049, 2336)
        JumpHandler(jump_key, wait_key, time_after_confirmation_range=time_after_confirmation).jump_with_confirmation()

    @staticmethod
    def jump_to_madatuzukeru():
        JumpHandler("mada-tudukeru", "is-madatuzukeru", time_after_confirmation_range=(1049, 1336),
                    react_keitai=False).jump_with_confirmation()

    @staticmethod
    def jump_to_vpn_setting():
        print("VPN設定メニューを開きます。")
        if ImageRecognizer.locate_center("vpn-icon-on"):
            JumpHandler("vpn-icon-on", "vpn-window", time_after_confirmation_range=(3049, 5336),
                        react_keitai=False, enable_adaptive_wait=True, react_error=False).jump_with_confirmation()
        elif ImageRecognizer.locate_center("vpn-icon-off"):
            JumpHandler("vpn-icon-off", "vpn-window", time_after_confirmation_range=(3049, 5336),
                        react_keitai=False, enable_adaptive_wait=True, react_error=False).jump_with_confirmation()

    @staticmethod
    def jump_to_vpn_switch_to_turn_on():
        print("VPNスイッチをONにします。")
        if ImageRecognizer.locate_center("vpn-invalid"):
            JumpHandler("vpn-off-state", "vpn-on-state", time_after_confirmation_range=(3049, 5336),
                        react_keitai=False, enable_adaptive_wait=True, react_error=False).jump_with_confirmation()

    @staticmethod
    def jump_to_vpn_switch_to_turn_off():
        print("VPNスイッチをOFFにします。")
        if ImageRecognizer.locate_center("vpn-on-state"):
            if not ImageRecognizer.locate_center("vpn-invalid"):
                JumpHandler("vpn-on-state", "vpn-off-state", time_after_confirmation_range=(3049, 5336),
                            react_keitai=False, enable_adaptive_wait=True, react_error=False).jump_with_confirmation()
                # if ImageRecognizer.locate_center("ad-close"):
                #     JumpHandler("ad-close", "vpn-off-state", time_after_confirmation_range=(3049, 5336),
                #                 react_keitai=False, enable_adaptive_wait=True, react_error=False).jump_with_confirmation()

    @staticmethod
    def jump_to_ffb_top_page():
        print("FFBトップページに移動します。")
        if ImageRecognizer.locate_center("ffb-icon"):
            JumpHandler("ffb-icon", "ffb-login", time_after_confirmation_range=(3049, 5336),
                        react_keitai=False, enable_adaptive_wait=True, react_error=False).jump_with_confirmation()
        else:
            assert True, "FFBトップページが見当たりません・・・"

    @staticmethod
    def jump_to_login_button():
        if ImageRecognizer.locate_center("ffb-login"):
            JumpHandler("ffb-login", "isStatus", time_after_confirmation_range=(3049, 5336),
                        react_keitai=True, enable_adaptive_wait=True, react_error=False).jump_with_confirmation()


class LoginManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoginManager, cls).__new__(cls)
        return cls._instance  # インスタンスを作るだけ（変数の初期化はしない）

    def __init__(self):
        if not hasattr(self, "initialized"):  # 初回だけ初期化
            self.account_table = {}
            self.switch_times = []
            self.pc_name = os.environ.get("COMPUTERNAME", "unknown")
            self.initialized = True  # 2回目以降の `__init__` で再初期化しない
            self.current_account = {}

    def add_account(self, switch_time, user_id, password):
        """アカウント情報を追加"""
        self.account_table[switch_time] = {"id": user_id, "password": password}
        self.switch_times = sorted(self.account_table.keys())
        self.current_account = self.get_current_account()

    def get_current_account(self):
        """現在の時間に対応するアカウント情報を取得（24時間ループ考慮）"""
        now = datetime.datetime.now().strftime("%H:%M")
        for t in reversed(self.switch_times):
            if t <= now:
                return self.account_table[t]
        return self.account_table[self.switch_times[-1]]  # 一番遅い時間をデフォルトに

    def check_account_switch(self):
        new_account = self.get_current_account()
        if new_account["id"] != self.current_account["id"]:
            self.current_account = new_account
            return True
        else:
            return False


class Notifier:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Notifier, cls).__new__(cls)
        return cls._instance  # インスタンスを作るだけ（変数の初期化はしない）

    def __init__(self):
        if not hasattr(self, "initialized"):  # 初回だけ初期化
            self.webhook_url = ""
            self.initialized = True  # 2回目以降の `__init__` で再初期化しない

    def add_webhook(self, webhook_url):
        self.webhook_url = webhook_url

    @staticmethod
    def generate_prefix():
        login_manager = LoginManager()
        pc_name = login_manager.pc_name
        user_name = login_manager.current_account["id"]
        prefix = f"🖥 **ホスト名:** {pc_name}\n"
        prefix += f"👤 **ユーザー名:** {user_name}\n"
        return prefix

    def send_discord_message(self, message: str):
        """
        Discordにテキストメッセージを送信する関数
        :param message: 送信するテキスト
        """
        full_message = self.generate_prefix()
        if message:
            full_message += "---------------------------------------------\n" + message + "\n---------------------------------------------\n"

        data = {"content": full_message}
        response = requests.post(self.webhook_url, json=data)

        if response.status_code == 204:
            print("✅ discordメッセージ送信成功！")
        else:
            print(f"⚠️ discordメッセージ送信エラー: {response.status_code}")
            print(response.text)

    def send_discord_image(self, image_path: str, caption: str = ""):
        """
        Discordに画像を送信する関数
        :param image_path: 送信する画像のファイルパス
        :param caption: 画像と一緒に送るメッセージ（オプション）
        """
        full_caption = self.generate_prefix()
        if caption:
            full_caption += "---------------------------------------------\n" + caption + "---------------------------------------------\n"

        with open(image_path, "rb") as image_file:
            files = {"file": image_file}
            data = {"content": full_caption}
            response = requests.post(self.webhook_url, data=data, files=files)

        if response.status_code == 204:
            print("✅ 画像送信成功！")
        else:
            print(f"⚠️ エラー: {response.status_code}")
            print(response.text)


class PenaltyCounter:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PenaltyCounter, cls).__new__(cls)
        return cls._instance  # インスタンスを作るだけ（変数の初期化はしない）

    def __init__(self):
        if not hasattr(self, "initialized"):  # 初回だけ初期化
            self.penalty_count = 0
            self.last_penalty_time = time.time()
            self.initialized = True  # 2回目以降の `__init__` で再初期化しない

    def check_penalty(self):
        dangerous_interval = 5  # hours
        if ImageRecognizer.locate_center("penalty"):
            if time.time() - self.last_penalty_time > dangerous_interval*3600:
                self.penalty_count = 1
            else:
                self.penalty_count += 1
            self.last_penalty_time = time.time()

            notifier = Notifier()
            if self.penalty_count > 5:
                notifier.send_discord_message(f"⚠️ ペナルティ警告がなされました。現在、{dangerous_interval}時間以内に連鎖した警告数は {self.penalty_count}回です。")
                time.sleep(30)
                Action.reset()
            else:
                notifier.send_discord_message(f"🚨 {dangerous_interval}時間以内に連鎖したペナルティ警告数が {self.penalty_count}回になりました。安全のため、プログラムを停止します。")
                sys.exit()


class Action:
    @staticmethod
    def reset(show_message=True):
        notifier = Notifier()
        if show_message:
            notifier.send_discord_message("⚠️ リセットシーケンスが開始されました。")

        # ipアドレスリセット
        JumpManager.jump_to_vpn_setting()
        JumpManager.jump_to_vpn_switch_to_turn_off()
        pyautogui.press("esc")
        time.sleep(10)
        ip_manager = IPManager()
        ip_manager.reset_ip()

        # ログインリセット
        JumpManager.jump_to_ffb_top_page()
        time.sleep(10)
        # ... id入力
        login_manager = LoginManager()
        account = login_manager.current_account
        pyautogui.hotkey("ctrl", "a")
        time.sleep(1)
        pyautogui.press("backspace")
        time.sleep(1)
        pyautogui.write(account["id"], 1)  # 1sec毎にタイプ
        pyautogui.press("tab")
        time.sleep(10)
        # ... pass入力
        pyautogui.hotkey("ctrl", "a")
        time.sleep(1)
        pyautogui.press("backspace")
        time.sleep(1)
        pyautogui.write(account["password"], 1)  # 1sec毎にタイプ
        time.sleep(10)
        # ... ログイン
        JumpManager.jump_to_vpn_setting()
        JumpManager.jump_to_vpn_switch_to_turn_on()
        pyautogui.press("esc")
        time.sleep(10)
        ip_manager.reset_ip()
        JumpManager.jump_to_login_button()
        time.sleep(5)
        while True:
            if ImageRecognizer.locate_center("isStatus"):
                if show_message:
                    notifier.send_discord_message("✅ リセットシーケンスが正常に終了し、ステータス画面が表示されました。")
                break
            if ImageRecognizer.locate_center("keitai"):
                break

    @staticmethod
    def home():
        pyautogui.press("home")
        time.sleep(0.5)  # 500ms
        if not ImageRecognizer.locate_center("isStatus"):
            pyautogui.press("end")
            time.sleep(0.5)
            JumpManager.jump_to_status()

    @staticmethod
    def go_to_manomori():
        if ImageRecognizer.locate_center("go-to-manomori"):
            JumpManager.jump_to_manomori()

    @staticmethod
    def go_to_challenge_character():
        if ImageRecognizer.locate_center("chara"):
            JumpManager.jump_to_challenge_character()
            pyautogui.press("tab")
            time.sleep(0.2)
            pyautogui.keyDown("shift")
            time.sleep(0.05)
            pyautogui.press("m")
            time.sleep(0.2)
            pyautogui.keyUp("shift")
            time.sleep(0.05)
            pyautogui.press("o")
            time.sleep(0.1)
            pyautogui.press("k")
            time.sleep(0.1)
            pyautogui.press("o")
            time.sleep(0.1)
            pyautogui.press("u")
            time.sleep(0.1)
            pyautogui.press("enter")
            time.sleep(5)
            pyautogui.press("tab")
            time.sleep(0.5)
            JumpManager.jump_to_status()

    @staticmethod
    def go_to_saishu():
        if ImageRecognizer.locate_center("go-to-manomori"):
            JumpManager.jump_to_saishu()

    @staticmethod
    def go_to_champ():
        if ImageRecognizer.locate_center("forced-champ"):
            JumpManager.jump_to_champ()
            pyautogui.press("end")
            time.sleep(0.5)
            JumpManager.jump_to_status()

    @staticmethod
    def go_to_next_manomori():
        if ImageRecognizer.locate_center("in-manomori"):
            pyautogui.press("end")
            time.sleep(0.5)
            if ImageRecognizer.locate_center("manomori-win"):
                JumpManager.jump_to_next_manomori()
            else:
                JumpManager.jump_to_status()

    @staticmethod
    def go_to_next_saishu():
        if ImageRecognizer.locate_center("in-last"):
            pyautogui.press("end")
            time.sleep(0.5)
            if ImageRecognizer.locate_center("manomori-win"):
                JumpManager.jump_to_next_saishu()
            else:
                JumpManager.jump_to_status()

    @staticmethod
    def go_to_sell_all_gomi_kouseki(collect_various_kouseki):
        Action.home()
        if ImageRecognizer.locate_center("auc"):
            JumpManager.jump_to_auction_from_status()
            pyautogui.press("end")
            time.sleep(1)
            JumpManager.jump_to_shuppin_select()
            Action.sell_loop_all_gomi_kouseki(collect_various_kouseki)
        Action.home()

    @staticmethod
    def go_to_sell_all_gomi_yoroi():
        Action.home()
        if ImageRecognizer.locate_center("bougu-ya"):
            JumpManager.jump_to_bougu()
            Action.sell_loop_all_gomi_yoroi()
        Action.home()

    @staticmethod
    def sell_loop_all_gomi_yoroi():
        forbidden_range = 7
        lower_limit_yoroi = 0

        while True:
            result_souko = ImageRecognizer.locate_center("souko")
            if result_souko:
                lower_limit_yoroi = result_souko[1]
                results_shino = ImageRecognizer.locate_all("shi-no")
                results_sell = ImageRecognizer.locate_all("sell")

                if results_sell:
                    click_ok = True
                    for result_sell in results_sell:
                        click_ok = True
                        if lower_limit_yoroi > result_sell[1]:
                            click_ok = False
                        for result_shino in results_shino:
                            lower_limit_y = result_shino[1] - forbidden_range
                            upper_limit_y = result_shino[1] + forbidden_range
                            if lower_limit_y <= result_sell[1] <= upper_limit_y:
                                click_ok = False
                                break
                        if click_ok:
                            pyautogui.click(result_sell[0], result_sell[1])
                            time.sleep(3)
                            JumpManager.jump_to_bougu()
                            break
                    if not click_ok:
                        break
                else:
                    break
            else:
                break

    @staticmethod
    def sell_loop_all_gomi_kouseki(collect_various_kouseki):
        forbidden_range = 4
        lower_limit_kouseki = 0

        while True:
            pyautogui.press("end")
            time.sleep(3)
            result_kouseki = ImageRecognizer.locate_center("kouseki")
            if result_kouseki:
                lower_limit_kouseki = result_kouseki[1]
            results_shiro = ImageRecognizer.locate_all("kouseki-shiro")
            results_mizu = ImageRecognizer.locate_all("kouseki-mizu")
            results_hi = ImageRecognizer.locate_all("kouseki-hi")
            results_zya = ImageRecognizer.locate_all("kouseki-zya")
            results_radio = ImageRecognizer.locate_all("radio-button-2")

            if results_radio:
                click_ok = True
                for result_radio in results_radio:
                    click_ok = True
                    if lower_limit_kouseki > result_radio[1]:
                        click_ok = False
                    for result_shiro in results_shiro:
                        lower_limit_y = result_shiro[1] - forbidden_range
                        upper_limit_y = result_shiro[1] + forbidden_range
                        if lower_limit_y <= result_radio[1] <= upper_limit_y:
                            click_ok = False
                            break

                    if collect_various_kouseki:
                        for result in results_mizu + results_hi + results_zya:
                            lower_limit_y = result[1] - forbidden_range
                            upper_limit_y = result[1] + forbidden_range
                            if lower_limit_y <= result_radio[1] <= upper_limit_y:
                                click_ok = False
                                break

                    if click_ok:
                        pyautogui.click(result_radio[0], result_radio[1], duration=0.5)
                        time.sleep(2)
                        pyautogui.press("tab")
                        time.sleep(2)
                        JumpManager.jump_to_shuppin_result()
                        JumpManager.jump_to_auction_from_shuppin_result()
                        pyautogui.press("end")
                        time.sleep(2)
                        JumpManager.jump_to_shuppin_select()
                        break
                if not click_ok:
                    break
            else:
                break

    @staticmethod
    def send_rare_kouseki():
        raw_range = 4

        Action.home()
        JumpManager.jump_to_auction_from_status()
        pyautogui.press("end")
        time.sleep(2)
        JumpManager.jump_to_shuppin_select()

        while True:
            pyautogui.press("end")
            time.sleep(3)
            results_shiro = ImageRecognizer.locate_all("kouseki-shiro")
            results_mizu = ImageRecognizer.locate_all("kouseki-mizu")
            results_hi = ImageRecognizer.locate_all("kouseki-hi")
            results_zya = ImageRecognizer.locate_all("kouseki-zya")
            results_radio = ImageRecognizer.locate_all("radio-button-2")

            if results_radio:
                click_ok = False
                is_shiro = False
                for result_radio in results_radio:
                    for result in results_shiro:
                        if result[1] - raw_range <= result_radio[1] <= result[1] + raw_range:
                            click_ok = True
                            is_shiro = True
                            break

                    if not click_ok:
                        for result in results_mizu + results_hi + results_zya:
                            if result[1] - raw_range <= result_radio[1] <= result[1] + raw_range:
                                click_ok = True
                                break

                    if click_ok:
                        pyautogui.click(result_radio[0], result_radio[1])
                        time.sleep(2)
                        pyautogui.press("tab")
                        time.sleep(2)
                        pyautogui.press("tab")
                        time.sleep(2)
                        pyautogui.press("x", presses=8, interval=0.2)
                        pyautogui.press("tab")
                        time.sleep(2)
                        pyautogui.press("2")
                        pyautogui.press("0", presses=13 if not is_shiro else 12, interval=0.2)

                        JumpManager.jump_to_shuppin_result()
                        JumpManager.jump_to_auction_from_shuppin_result()
                        pyautogui.press("end")
                        time.sleep(2)
                        JumpManager.jump_to_shuppin_select()
                        break
                if not click_ok:
                    break
            else:
                break
        Action.home()


class HandleRecaptcha:
    @staticmethod
    def check_recaptcha(jump_key, wait_key):
        time_after_confirmation = (849, 1036)  # 849 + Random(0, 187)
        JumpHandler(
            jump_key=jump_key,
            wait_key=wait_key,
            time_after_confirmation_range=time_after_confirmation,
            react_keitai=False,
            enable_adaptive_wait=False
        ).jump_with_confirmation()

    @staticmethod
    def wait_for_captcha_ready():
        waiting_interval = 0.2  # 200ms
        wait_keys = ["cloudflare-check", "recaptcha-check", "cloudflare-check-02"]
        time_after_confirmation = random.randint(815, 1129)  # 815 + Random(0, 314)

        print("CAPTCHAのチェックボタンが描画されるのを待ちます。")
        while True:
            if any(ImageRecognizer.locate_center(key) for key in wait_keys):
                break
            time.sleep(waiting_interval)

        print("CAPTCHAのチェックボタンの描画が完了しました。")
        time.sleep(time_after_confirmation / 1000)

    @staticmethod
    def capture_screenshot(suffix):
        screenshot = pyautogui.screenshot()

        documents_path = os.path.expanduser("~/Documents")
        if not os.path.exists(documents_path):
            documents_path = os.path.join(os.path.expanduser("~"), "OneDrive", "ドキュメント")
        save_directory = os.path.join(documents_path, "ffb", "macro-capture")
        os.makedirs(save_directory, exist_ok=True)

        counter = 1
        while True:
            file_path = os.path.join(save_directory, f"{counter:04d}_screenshot_{suffix}.png")
            if not os.path.exists(file_path):
                break
            counter += 1

        screenshot.save(file_path)
        print(f"📸 スクリーンショットを保存しました: {file_path}")


class Macro:
    @staticmethod
    def collect_material(collect_mode: str, collect_yoroi: bool, collect_various_kouseki: bool):
        notifier = Notifier()
        idling_time = 0

        notifier.send_discord_message("⚠️ FFBオート周回マクロが開始されました。ログインシーケンスを開始します。")
        Action.reset(False)
        notifier.send_discord_message("✅ ログインシーケンスが終了しました。オート周回を開始します。")

        while True:
            login_manager = LoginManager()
            if login_manager.check_account_switch():
                notifier.send_discord_message("⚠️ アカウント切り替え時刻になりました。切り替えシーケンスを開始します。")
                Action.reset()
                notifier.send_discord_message("✅ アカウント切り替えが正常に終了しました。周回を開始します。")

            Action.home()
            if collect_yoroi:
                Action.go_to_sell_all_gomi_yoroi()
            Action.go_to_sell_all_gomi_kouseki(collect_various_kouseki)

            loop_num = random.randint(375, 854)
            for _ in range(loop_num):
                pyautogui.press("home")
                time.sleep(0.5)

                # ジャンプフラグを初期化して、このループ内で一度でもジャンプが行われたかどうかを監視する
                JumpHandler.jump_used = False
                start_time = time.time()
                if collect_mode == "manomori":
                    Macro.step_manomori()
                elif collect_mode == "saishu":
                    Macro.step_saishu()

                # stepのジャンプによってペナルティ警告ページに飛ばされていないかチェック
                penalty_counter = PenaltyCounter()
                penalty_counter.check_penalty()

                # step関数内でジャンプが発動していたら休憩の抽選を行う
                # 発動していないなら、アイドリング時間として加算する。アイドリング時間が一定基準を超えるとリセット発動。
                if JumpHandler.jump_used:
                    idling_time = 0
                    if random.randint(1, 1000) > 995:
                        rest_time = random.randint(1, 600000) / 1000
                        print(f"約 {rest_time / 60:.2f} min の休憩に入ります。")
                        time.sleep(rest_time)
                        print(f"休憩終了。メインループに戻ります。")
                else:
                    time.sleep(1)
                    idling_time += time.time() - start_time

                if idling_time > 600:
                    Action.reset()

    @staticmethod
    def kamo_gari():
        Action.home()
        while True:
            Action.go_to_challenge_character()
            Action.go_to_champ()

    @staticmethod
    def step_manomori():
        Action.go_to_manomori()
        Action.go_to_next_manomori()
        Action.go_to_champ()
        Macro.hundle_keitai_denwa()


    @staticmethod
    def step_saishu():
        Action.go_to_saishu()
        Action.go_to_next_saishu()
        Action.go_to_champ()
        Macro.hundle_keitai_denwa()

    @staticmethod
    def hundle_keitai_denwa():
        if ImageRecognizer.locate_center("keitai"):
            notifier = Notifier()
            notifier.send_discord_message("⚠️ bot検知ページに遷移しました。認証突破を試みます。")
            HandleRecaptcha.wait_for_captcha_ready()
            HandleRecaptcha.capture_screenshot("before")

            checks = [
                ("recaptcha-check", "recaptcha-success"),
                ("cloudflare-check", "cloudflare-success"),
                ("cloudflare-check-02", "cloudflare-success-02")
            ]

            for check_key, wait_key in checks:
                if ImageRecognizer.locate_center(check_key):
                    HandleRecaptcha.check_recaptcha(check_key, wait_key)

            HandleRecaptcha.capture_screenshot("after")
            JumpManager.jump_to_madatuzukeru()
            HandleRecaptcha.capture_screenshot("negirai")
            JumpManager.jump_to_status()
            if ImageRecognizer.locate_center("isStatus"):
                notifier.send_discord_message("✅ bot検知ページの認証突破に成功しステータス画面に遷移しました。")
            else:
                notifier.send_discord_message("🚨 bot検知ページの認証突破に失敗しました。")


class ImageRecognizer:
    IMAGE_PARAMS = {
        "champ": {"filename": "champ.png", "confidence": 0.85, "region": (11, 124, 1120, 815)},
        "forced-champ": {"filename": "forced-champ.png", "confidence": 0.75, "region": (557, 220, 1342, 810)},
        "anti-macro-01": {"filename": "anti-macro-01.png", "confidence": 0.9, "region": (9, 131, 344, 336)},
        "mada-tudukeru": {"filename": "mada-tudukeru.png", "confidence": 0.8, "region": (1, 124, 826, 899)},
        "to-status": {"filename": "to-status.png", "confidence": 0.8, "region": (8, 118, 633, 916)},
        "go-to-manomori": {"filename": "manomori-pulldown-2.png", "confidence": 0.8, "region": (717, 236, 1174, 779)},
        "in-manomori": {"filename": "in-manomori.png", "confidence": 0.8, "region": (2, 116, 563, 871)},
        "manomori-win": {"filename": "manomori-win.png", "confidence": 0.8, "region": (8, 138, 595, 890)},
        "go-to-champ": {"filename": "champ.png", "confidence": 0.8, "region": (11, 130, 1006, 597)},
        "anti-macro-02": {"filename": "anti-macro-02.png", "confidence": 0.9, "region": (5, 133, 340, 327)},
        "anti-macro-00": {"filename": "anti-macro-00.png", "confidence": 0.9, "region": (61, 110, 608, 669)},
        "radio-button-2": {"filename": "radio-button.png", "confidence": 0.9, "region": (313, 120, 1143, 905)},
        "kouseki-shiro": {"filename": "shiro-2.png", "confidence": 0.7, "region": (377, 120, 1141, 913)},
        "kouseki-mizu": {"filename": "mizu.png", "confidence": 0.7, "region": (334, 119, 1071, 914)},
        "kouseki-hi": {"filename": "fire.png", "confidence": 0.7, "region": (293, 123, 1102, 909)},
        "kouseki-zya": {"filename": "zya.png", "confidence": 0.7, "region": (437, 126, 920, 900)},
        "kouseki": {"filename": "kouseki.png", "confidence": 0.85, "region": (322, 119, 1079, 913)},
        "acu-shuppin": {"filename": "shuppin.png", "confidence": 0.75, "region": (760, 123, 848, 902)},
        "back-to-auc": {"filename": "back-to-auc.png", "confidence": 0.8, "region": (2, 125, 453, 801)},
        "keitai": {"filename": "keitai.png", "confidence": 0.9, "region": (1, 122, 788, 450)},
        "cloudflare-check": {"filename": "cloudflare-check.png", "confidence": 0.8, "region": (1, 125, 619, 853)},
        "cloudflare-success": {"filename": "cloudflare-success.png", "confidence": 0.8, "region": (1, 123, 644, 783)},
        "recaptcha-check": {"filename": "recaptcha-check.png", "confidence": 0.8, "region": (1, 120, 793, 907)},
        "recaptcha-success": {"filename": "recaptcha-success.png", "confidence": 0.8, "region": (1, 122, 725, 912)},
        "is-auc": {"filename": "is-auction.png", "confidence": 0.8, "region": (1, 217, 549, 314)},
        "is-shuppin": {"filename": "is-shuppin.png", "confidence": 0.8, "region": (384, 144, 1038, 560)},
        "shuppin-done": {"filename": "shuppin-done.png", "confidence": 0.8, "region": (1, 120, 539, 239)},
        "is-champ": {"filename": "is-champ.png", "confidence": 0.8, "region": (5, 122, 1877, 163)},
        "cloudflare-check-02": {"filename": "cloudflare-check-02.png", "confidence": 0.8,
                                "region": (1, 122, 1082, 885)},
        "cloudflare-success-02": {"filename": "cloudflare-success-02.png", "confidence": 0.8,
                                  "region": (1, 122, 1137, 909)},
        "is-madatuzukeru": {"filename": "is-madatuzukeru.png", "confidence": 0.8, "region": (1, 121, 872, 899)},
        "go-to-last": {"filename": "last-pulldown.png", "confidence": 0.75, "region": (888, 201, 1006, 718)},
        "in-last": {"filename": "in-last.png", "confidence": 0.8, "region": (1, 112, 1079, 573)},
        "error": {"filename": "error.png", "confidence": 0.8, "region": (1, 120, 1904, 667)},
        "chara": {"filename": "chara.png", "confidence": 0.8, "region": (1, 124, 1411, 786)},
        "is-chara": {"filename": "is-chara.png", "confidence": 0.9, "region": (1, 124, 681, 433)},
        "shi-no": {"filename": "shi-no.png", "confidence": 0.75, "region": (1, 125, 945, 904)},
        "souko": {"filename": "souko.png", "confidence": 0.8, "region": (2, 127, 982, 902)},
        "sell": {"filename": "sell.png", "confidence": 0.8, "region": (3, 122, 956, 906)},
        "isStatus": {"filename": "is-status.png", "confidence": 0.85, "region": (17, 127, 961, 635)},
        "auc": {"filename": "auc.png", "confidence": 0.85, "region": (163, 218, 973, 598)},
        "go-to-shuppin": {"filename": "to-shuppin.png", "confidence": 0.8, "region": (1, 127, 618, 900)},
        "bougu-ya": {"filename": "bougu-ya.png", "confidence": 0.8, "region": (2, 123, 1205, 738)},
        "is-bougu-ya": {"filename": "is-bougu-ya.png", "confidence": 0.8, "region": (1, 126, 1063, 891)},
        "ad-close": {"filename": "ad-close.png", "confidence": 0.8, "region": (1014, 1, 886, 764)},
        "vpn-icon-on": {"filename": "vpn-icon-on.png", "confidence": 0.8, "region": (607, 1, 1307, 300)},
        "vpn-icon-off": {"filename": "vpn-icon-off.png", "confidence": 0.8, "region": (607, 1, 1307, 300)},
        "vpn-window": {"filename": "vpn-window.png", "confidence": 0.8, "region": (1014, 1, 886, 764)},
        "vpn-on-state": {"filename": "vpn-on-state.png", "confidence": 0.8, "region": (1014, 1, 886, 764)},
        "vpn-off-state": {"filename": "vpn-off-state.png", "confidence": 0.8, "region": (1014, 1, 886, 764)},
        "vpn-invalid": {"filename": "vpn-invalid.png", "confidence": 0.8, "region": (1014, 1, 886, 764)},
        "ffb-icon": {"filename": "ffb-icon.png", "confidence": 0.8, "region": (516, 1, 1905, 229)},
        "ffb-login": {"filename": "ffb-login.png", "confidence": 0.8, "region": (516, 1, 1905, 502)},
        "penalty": {"filename": "penalty.png", "confidence": 0.8, "region": (1, 1, 1905, 502)},
    }

    IMAGE_FOLDER = "temp-image"  # 画像フォルダのパス

    @staticmethod
    def locate_center(key):
        params = ImageRecognizer.IMAGE_PARAMS.get(key)
        if not params:
            print(f"⚠️ '{key}' の画像パラメータが登録されていません。")
            return None

        filename = os.path.join(ImageRecognizer.IMAGE_FOLDER, params["filename"])
        region = params["region"]  # (x, y, width, height)
        confidence = params["confidence"]

        screenshot = pyautogui.screenshot(region=region)
        screenshot = np.array(screenshot)
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)

        template = cv2.imread(filename, cv2.IMREAD_COLOR)
        if template is None:
            print(f"⚠️ '{filename}' の画像が見つかりませんでした。")
            return None

        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val < confidence:
            return None

        h, w = template.shape[:2]
        screen_x, screen_y = region[:2]  # モニタ座標のオフセットを取得
        return (max_loc[0] + w // 2 + screen_x, max_loc[1] + h // 2 + screen_y)

    @staticmethod
    def locate_all(key):
        params = ImageRecognizer.IMAGE_PARAMS.get(key)
        if not params:
            print(f"⚠️ '{key}' の画像パラメータが登録されていません。")
            return []

        filename = os.path.join(ImageRecognizer.IMAGE_FOLDER, params["filename"])
        region = params["region"]  # (x, y, width, height)
        confidence = params["confidence"]

        screenshot = pyautogui.screenshot(region=region)
        screenshot = np.array(screenshot)
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)

        template = cv2.imread(filename, cv2.IMREAD_COLOR)
        if template is None:
            print(f"⚠️ '{filename}' の画像が見つかりませんでした。")
            return []

        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(result >= confidence)

        h, w = template.shape[:2]
        screen_x, screen_y = region[:2]  # モニタ座標のオフセットを取得
        return [(pt[0] + w // 2 + screen_x, pt[1] + h // 2 + screen_y) for pt in zip(*loc[::-1])]
