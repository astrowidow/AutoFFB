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
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
import setproctitle
import atexit


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
            options.add_argument("--disable-blink-features=AutomationControlled")  # 自動操作検出回避

            # ✅ ChromeDriver のパスを取得（pyinstaller に対応）
            def get_chromedriver_path():
                if getattr(sys, 'frozen', False):
                    return os.path.join(sys._MEIPASS, "chromedriver.exe")
                else:
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    return os.path.join(script_dir, "chromedriver.exe" if os.name == "nt" else "chromedriver")
            driver_path = get_chromedriver_path()

            service = Service(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=options)

            # ✅ navigator.webdriver の隠蔽
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            })

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
            pyautogui.moveTo(target_x, target_y, 0.2)
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
                adaptive_wait_time = int(elapsed_time * 1200)
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
            time_after_confirmation = (2149, 2336)
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
        vpn_manager = VpnManager()
        if vpn_manager.use_vpn:
            print("VPNスイッチをONにします。")
            if ImageRecognizer.locate_center("vpn-invalid"):
                JumpHandler("vpn-off-state", "vpn-on-state", time_after_confirmation_range=(3049, 5336),
                            react_keitai=False, enable_adaptive_wait=True, react_error=False).jump_with_confirmation()
        else:
            print("VPNが有効化されていません。VPNMangerクラスを参照して、有効化してください。")

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
            self.enable_message = True
            self.ok_post_interval = 3*60*60  # 3時間
            self.last_post_time = time.time()
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
        if self.enable_message:
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
        self.last_post_time = time.time()

    def send_discord_image(self, image_path: str, caption: str = ""):
        """
        Discordに画像を送信する関数
        :param image_path: 送信する画像のファイルパス
        :param caption: 画像と一緒に送るメッセージ（オプション）
        """
        if self.enable_message:
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
        self.last_post_time = time.time()

    def send_ok_post(self):
        if time.time() - self.last_post_time > self.ok_post_interval:
            self.send_discord_message("✅ 定期報告：正常に周回中！")


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
            if self.penalty_count <= 5:
                notifier.send_discord_message(f"⚠️ ペナルティ警告がなされました。現在、{dangerous_interval}時間以内に連鎖した警告数は {self.penalty_count}回です。")
                time.sleep(30)
                Action.reset()
            else:
                notifier.send_discord_message(f"🚨 {dangerous_interval}時間以内に連鎖したペナルティ警告数が {self.penalty_count}回になりました。")
                sys.exit()


class VpnManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VpnManager, cls).__new__(cls)
        return cls._instance  # インスタンスを作るだけ（変数の初期化はしない）

    def __init__(self):
        if not hasattr(self, "initialized"):  # 初回だけ初期化
            self.use_vpn = False
            self.user_setting = False
            self.initialized = True  # 2回目以降の `__init__` で再初期化しない

    def enable(self, flag=True):
        self.use_vpn = flag
        self.user_setting = flag


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
        vpn_manager = VpnManager()
        if vpn_manager.use_vpn:
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
                            pyautogui.moveTo(result_sell[0], result_sell[1], 0.2)
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
                        pyautogui.moveTo(result_radio[0], result_radio[1], 0.2)
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
                        pyautogui.moveTo(result_radio[0], result_radio[1], 0.2)
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
    DISPLAY_WIDTH = 1920
    DISPLAY_HEIGHT = 1080

    @staticmethod
    def login_another_window():
        # ✅ Winキーと同じ効果があるショートカット。レジストリでWin無効のマシンもあるので。
        pyautogui.hotkey("ctrl", "esc")
        time.sleep(2)  # スタートメニューが開くのを待機

        # ✅ "chrome" を入力
        pyautogui.write("chrome", interval=0.2)
        time.sleep(2)  # 入力が完了するのを待つ

        # ✅ Enterキーを押してChromeを開く
        pyautogui.press("enter")
        time.sleep(3)  # Chromeの起動を待つ（環境によって調整）

        # VPNは切っておく。
        vpn_manager = VpnManager()
        vpn_manager.use_vpn = False
        Action.reset(show_message=False)

    @staticmethod
    def check_recaptcha2(jump_key, wait_key):
        notifier = Notifier()

        time_after_confirmation = random.randint(349, 836)  # 849 + Random(0, 187)
        check_success = False
        challenge_count = 0
        while challenge_count < 30:
            location = ImageRecognizer.locate_center(jump_key)
            if location:
                # call key to key
                pyautogui.keyDown("pageup")
                time.sleep(0.2)
                pyautogui.keyUp("pageup")

                # wait success
                start_time = time.time()
                check_interval = 0.1  # sec
                while time.time() - start_time < 600:
                    if ImageRecognizer.locate_center(wait_key):
                        check_success = True
                        break
                    time.sleep(check_interval)
                if check_success:
                    break
                else:
                    notifier.send_discord_message(
                        "🚨 一定時間かけても人間認証を突破できませんでした。")
                    sys.exit()
        time.sleep(time_after_confirmation / 1000)

    @staticmethod
    def check_recaptcha(jump_key, wait_key):
        notifier = Notifier()

        time_after_confirmation = random.randint(349, 836)  # 849 + Random(0, 187)
        check_success = False
        start_time = time.time()
        challenge_count = 0
        while challenge_count < 30:
            location = ImageRecognizer.locate_center(jump_key)
            if location:
                # ip_manager = IPManager()
                # ip_manager.wait_for_ip_recovery()

                # 人間っぽい動きにするために細かく制御
                # ... 指定座標までマウスを移動させる
                pointer_moving_duration = random.randint(1740, 3005) / 1000
                start_x = random.randint(400, 1800)
                start_y = random.randint(500, 800)
                target_x = location[0] + random.randint(-6, 6)
                target_y = location[1] + random.randint(-6, 6)
                print(f"id: {jump_key}, x: {target_x}, y: {target_y}")
                HandleRecaptcha.human_like_mouse_move((start_x, start_y), (target_x, target_y), pointer_moving_duration)
                # ... クリック
                click_duration = random.randint(32, 582) / 1000
                pyautogui.mouseDown()
                time.sleep(click_duration)
                pyautogui.mouseUp()
                # ... クリック後遠ざかる
                pointer_moving_duration = random.randint(1030, 1542) / 1000
                start_x = target_x
                start_y = target_y
                target_x = location[0] + random.randint(540, 840)
                target_y = location[1] + random.randint(340, 540)
                HandleRecaptcha.human_like_mouse_move((start_x, start_y), (target_x, target_y), pointer_moving_duration)

                check_interval = 0.1  # sec
                while True:
                    if ImageRecognizer.locate_center(wait_key):
                        check_success = True
                        break
                    elif ImageRecognizer.locate_center(jump_key):
                        challenge_count += 1
                        randint = random.randint(1,100)
                        if randint > 90:
                            randint = random.randint(300000, 600000)
                            sleepsec = randint/1000
                            print(f"{sleepsec}秒休憩")
                            time.sleep(sleepsec)
                        break
                    time.sleep(check_interval)
                if check_success:
                    break
        if not check_success:
            notifier.send_discord_message("🚨 一定時間かけても人間認証を突破できませんでした。")
            sys.exit()
        time.sleep(time_after_confirmation / 1000)

    @staticmethod
    def wait_for_captcha_ready():
        waiting_interval = 0.5  # 500ms
        wait_keys = ["cloudflare-check", "recaptcha-check", "cloudflare-check-02"]
        time_after_confirmation = random.randint(515, 629)

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

    @classmethod
    def generate_path(cls, start, end):
        x1, y1 = start
        x2, y2 = end
        num_segments = max(2, random.randint(3, 6))  # 分割数を最低2に設定
        points = [start]
        segment_durations = []  # 各区間の待機時間を格納

        prev_x, prev_y = x1, y1
        for _ in range(num_segments - 1):
            while True:
                mid_x = np.interp(random.random(), [0, 1], [prev_x, x2])
                mid_y = np.interp(random.random(), [0, 1], [prev_y, y2])
                offset_x = random.uniform(-abs(prev_x - x2) * 0.5, abs(prev_x - x2) * 0.5)
                offset_y = random.uniform(-abs(prev_y - y2) * 0.5, abs(prev_y - y2) * 0.5)
                new_x = int(mid_x + offset_x)
                new_y = int(mid_y + offset_y)

                # 画面外にならないようにチェック
                if 0 <= new_x <= cls.DISPLAY_WIDTH and 0 <= new_y <= cls.DISPLAY_HEIGHT:
                    break

            points.append((new_x, new_y))
            prev_x, prev_y = new_x, new_y
            segment_durations.append(random.uniform(0.05, 0.2))  # 各頂点でのスリープ時間を設定
        points.append(end)
        segment_durations.append(0)  # 最後の目標地点では停止しない

        path = []
        for i in range(len(points) - 1):
            p1, p2 = points[i], points[i + 1]
            while True:
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                mid_x = (p1[0] + p2[0]) / 2 + random.uniform(-abs(dx) * 0.8, abs(dx) * 0.8)
                mid_y = (p1[1] + p2[1]) / 2 + random.uniform(-abs(dy) * 0.8, abs(dy) * 0.8)
                p_mid = (int(mid_x), int(mid_y))

                # 画面外にならないようにチェック
                if 0 <= p_mid[0] <= cls.DISPLAY_WIDTH and 0 <= p_mid[1] <= cls.DISPLAY_HEIGHT:
                    break

            def bezier_curve(t, p0, p1, p2):
                return (1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(p1) + t ** 2 * np.array(p2)

            t_vals = np.linspace(0, 1, num=30)
            t_vals = t_vals ** 2 / (t_vals ** 2 + (1 - t_vals) ** 2)  # 加減速を模擬

            for t in t_vals:
                path.append(bezier_curve(t, p1, p_mid, p2))

        return np.array(path), points, segment_durations

    @classmethod
    def human_like_mouse_move(cls, start, end, duration=1.5):
        path, points, segment_durations = cls.generate_path(start, end)
        total_segment_pause = sum(segment_durations)
        available_move_time = duration - total_segment_pause  # 実際の移動に使える時間
        total_steps = len(path)
        min_time_step = 0.05
        step_duration = available_move_time / total_steps

        if step_duration < min_time_step:
            skip_factor = int(np.ceil(min_time_step / step_duration))
            path = path[::skip_factor]
            total_steps = len(path)
            step_duration = available_move_time / total_steps

        step_idx = 0
        for i, (x, y) in enumerate(path):
            pyautogui.moveTo(int(x), int(y), duration=step_duration)
            if i > 0 and i % max(1, len(path) // len(segment_durations)) == 0:
                if step_idx < len(segment_durations):
                    time.sleep(segment_durations[step_idx])  # 各頂点で停止
                    step_idx += 1
        pyautogui.moveTo(end[0], end[1], duration=0.05)

    @classmethod
    def visualize_path(cls, start, end, duration=1.5):
        path, points, _ = cls.generate_path(start, end)
        plt.figure(figsize=(6, 6))
        plt.plot(path[:, 0], path[:, 1], marker='o', linestyle='-', color='b', label='Mouse Path')
        plt.scatter(*zip(*points), color='r', label='Control Points')
        plt.legend()
        plt.title("Simulated Human-like Mouse Movement")
        plt.gca().invert_yaxis()
        plt.show()


class Macro:
    @staticmethod
    def on_exit():
        notifier = Notifier()
        notifier.enable_message = True
        notifier.send_discord_message("🚨 プログラムを終了します。手動で原因調査と復帰を試みてください。")

    @staticmethod
    def collect_material(collect_mode: str, collect_yoroi: bool, collect_various_kouseki: bool):
        atexit.register(Macro.on_exit)
        notifier = Notifier()
        vpn_manager = VpnManager()
        idling_time = 0

        # 初期画面がステータス画面かどうかでイニシャライズ方法を変える。
        if ImageRecognizer.locate_center("isStatus"):
            notifier.send_discord_message("✅ FFBオート周回マクロが開始されました。オート周回を開始します。")
            if vpn_manager.use_vpn:
                JumpManager.jump_to_vpn_setting()
                JumpManager.jump_to_vpn_switch_to_turn_on()
                pyautogui.press("esc")
                time.sleep(10)
                ip_manager = IPManager()
                ip_manager.reset_ip()
        else:
            notifier.send_discord_message("⚠️ FFBオート周回マクロが開始されました。ログインシーケンスを開始します。")
            Action.reset(False)
            notifier.send_discord_message("✅ ログインシーケンスが終了しました。オート周回を開始します。")

        # ここから周回開始
        while True:
            login_manager = LoginManager()
            if login_manager.check_account_switch():
                notifier.send_discord_message("⚠️ アカウント切り替え時刻になりました。切り替えシーケンスを開始します。")
                if not vpn_manager.use_vpn:
                    notifier.send_discord_message("⚠️ VPNを使用しない設定になっているため、ログイン情報リセットのために40分スリープします。")
                    time.sleep(40 * 60)
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

                idling_thresh = 10  # min
                if idling_time > 60*idling_thresh:
                    notifier.send_discord_message(f"⚠️ 突っかかっているみたいで、ページ遷移が{idling_thresh}分間行われていません。一度ログインし直します。")
                    Action.reset()

                notifier.send_ok_post()

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

            # まずは怪しくないChromeセッションを立ち上げる
            HandleRecaptcha.login_another_window()
            if ImageRecognizer.locate_center("keitai"):
                HandleRecaptcha.wait_for_captcha_ready()
                # HandleRecaptcha.capture_screenshot("before")

                checks = [
                    ("recaptcha-check", "recaptcha-success"),
                    ("cloudflare-check", "cloudflare-success"),
                    ("cloudflare-check-02", "cloudflare-success-02")
                ]

                for check_key, wait_key in checks:
                    if ImageRecognizer.locate_center(check_key):
                        HandleRecaptcha.check_recaptcha(check_key, wait_key)

                notifier.enable_message = False  # 高確率でエラーページに飛ばされるので、このタイミングで飛ばされた場合は想定どおりとして通知をしない（うるさいから）
                # HandleRecaptcha.capture_screenshot("after")
                JumpManager.jump_to_madatuzukeru()
                # HandleRecaptcha.capture_screenshot("negirai")
                JumpManager.jump_to_status()
                notifier.enable_message = True

            if ImageRecognizer.locate_center("isStatus"):
                # 立ち上がっているはずのChrome新Windowを閉じる
                pyautogui.hotkey("alt", "f4")
                time.sleep(2)
                # debugモードのChromeの方でアカウントにログインし直して、認証突破扱いになるはず。
                vpn_manager = VpnManager()
                vpn_manager.use_vpn = vpn_manager.user_setting
                Action.reset(show_message=False)
                if ImageRecognizer.locate_center("isStatus"):
                    notifier.send_discord_message("✅ bot検知ページの認証突破に成功しステータス画面に遷移しました。")
                else:
                    notifier.send_discord_message("🚨 bot検知ページの認証突破に失敗しました。code:01")
                    sys.exit()
            else:
                notifier.send_discord_message("🚨 bot検知ページの認証突破に失敗しました。code:02")
                sys.exit()


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
        "is-shuppin": {"filename": "is-shuppin.png", "confidence": 0.8, "region": (384, 144, 1038, 878)},
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
