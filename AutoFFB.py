import os
import time
import datetime
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pyautogui
import requests


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
            service = Service()  # ChromeDriverのパスは自動検出
            driver = webdriver.Chrome(service=service, options=options)

            driver.get("https://api64.ipify.org")
            ip = driver.find_element("tag name", "body").text.strip()
            driver.quit()
            return ip
        except Exception as e:
            print(f"⚠️ Chrome経由でのIP取得エラー: {e}")
            return ""

    def wait_for_ip_recovery(self, max_wait_time=1800, target_stable_time=600, check_interval=30):
        elapsed_time = 0
        last_ip = ""
        stable_time = 0

        while elapsed_time < max_wait_time:
            current_ip = self.get_public_ip()

            if not current_ip:
                print("⚠️ 現在のIPアドレス取得に失敗。再試行します...")
            elif current_ip == self.initial_ip:
                if elapsed_time > 0:
                    print("✅ IPアドレスが元に戻りました。通常処理を続行します。")
                    self.log_ip_change(self.initial_ip, self.initial_ip, elapsed_time)
                return
            else:
                if current_ip != last_ip:
                    last_ip = current_ip
                    stable_time = 0
                else:
                    stable_time += check_interval

                if stable_time >= target_stable_time:
                    print(f"⏳ 新しいIP {last_ip} をマスターとして採用 (維持時間: {stable_time}秒)")
                    self.log_ip_change(self.initial_ip, last_ip, elapsed_time)
                    self.initial_ip = last_ip  # 新しいIPをマスターにする
                    return
                else:
                    print(
                        f"⚠️ IP変化: {self.initial_ip} → {current_ip} (維持時間: {stable_time}s / 目標: {target_stable_time}s)")

            time.sleep(check_interval)
            elapsed_time += check_interval

        print("⚠️ 最大待機時間を超えました。処理を継続します。")

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
    def __init__(self, jump_key, wait_key, time_after_key_down=20, time_after_confirmation_range=(5000, 10000),
                 offset_x=0, offset_y=0, react_keitai=True, enable_adaptive_wait=True):
        self.jump_key = jump_key
        self.wait_key = wait_key
        self.time_after_key_down = time_after_key_down
        self.time_after_confirmation_range = time_after_confirmation_range
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.react_keitai = react_keitai
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
            react_error=True
        )

        if reason == "ErrorInterrupt":
            print(f"エラーが発生したため、ステータスに戻します。 (元の遷移 from:{self.jump_key} to:{self.wait_key})")
            self.jump_with_confirmation_core(
                jump_key="to-status", wait_key="isStatus",
                time_after_key_down=100,
                time_after_confirmation=10000,
                react_keitai=self.react_keitai,
                react_error=False
            )

    def jump_with_confirmation_core(self, jump_key, wait_key, time_after_key_down, time_after_confirmation, offset_x=0,
                                    offset_y=0, react_keitai=True, enable_adaptive_wait=True, react_error=True):
        location = pyautogui.locateCenterOnScreen(f"{jump_key}.png", confidence=0.8)
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
            if pyautogui.locateCenterOnScreen(f"{wait_key}.png", confidence=0.8):
                return time.time() - start_time, "PageTransition"
            elif pyautogui.locateCenterOnScreen("keitai.png", confidence=0.8):
                if react_keitai:
                    return time.time() - start_time, "KeitaiInterrupt"
            elif pyautogui.locateCenterOnScreen("error.png", confidence=0.8):
                if react_error:
                    return time.time() - start_time, "ErrorInterrupt"
            time.sleep(waiting_interval/1000)
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
        if pyautogui.locateCenterOnScreen(f"{wait_key}.png", confidence=0.8):
            time_after_confirmation = (18549, 26636)
        else:
            time_after_confirmation = (2049, 2336)
        JumpHandler(jump_key, wait_key, time_after_confirmation_range=time_after_confirmation).jump_with_confirmation()

    @staticmethod
    def jump_to_madatuzukeru():
        JumpHandler("mada-tudukeru", "is-madatuzukeru", time_after_confirmation_range=(1049, 1336),
                    react_keitai=False).jump_with_confirmation()


class Action:
    @staticmethod
    def home():
        pyautogui.press("home")
        time.sleep(0.5)  # 500ms
        if not pyautogui.locateCenterOnScreen("isStatus.png", confidence=0.8):
            pyautogui.press("end")
            time.sleep(0.5)
            JumpManager.jump_to_status()

    @staticmethod
    def go_to_manomori():
        if pyautogui.locateCenterOnScreen("go-to-manomori.png", confidence=0.8):
            JumpManager.jump_to_manomori()

    @staticmethod
    def go_to_challenge_character():
        if pyautogui.locateCenterOnScreen("chara.png", confidence=0.8):
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
        if pyautogui.locateCenterOnScreen("go-to-manomori.png", confidence=0.8):
            JumpManager.jump_to_saishu()

    @staticmethod
    def go_to_champ():
        if pyautogui.locateCenterOnScreen("forced-champ.png", confidence=0.8):
            JumpManager.jump_to_champ()
            pyautogui.press("end")
            time.sleep(0.5)
            JumpManager.jump_to_status()

    @staticmethod
    def go_to_next_manomori():
        if pyautogui.locateCenterOnScreen("in-manomori.png", confidence=0.8):
            pyautogui.press("end")
            time.sleep(0.5)
            if pyautogui.locateCenterOnScreen("manomori-win.png", confidence=0.8):
                JumpManager.jump_to_next_manomori()
            else:
                JumpManager.jump_to_status()

    @staticmethod
    def go_to_next_saishu():
        if pyautogui.locateCenterOnScreen("in-last.png", confidence=0.8):
            pyautogui.press("end")
            time.sleep(0.5)
            if pyautogui.locateCenterOnScreen("manomori-win.png", confidence=0.8):
                JumpManager.jump_to_next_saishu()
            else:
                JumpManager.jump_to_status()

    @staticmethod
    def go_to_sell_all_gomi_kouseki(collect_various_kouseki):
        Action.home()
        if pyautogui.locateCenterOnScreen("auc.png", confidence=0.8):
            JumpManager.jump_to_auction_from_status()
            pyautogui.press("end")
            time.sleep(1)
            JumpManager.jump_to_shuppin_select()
            Action.sell_loop_all_gomi_kouseki(collect_various_kouseki)
        Action.home()

    @staticmethod
    def go_to_sell_all_gomi_yoroi():
        Action.home()
        if pyautogui.locateCenterOnScreen("bougu-ya.png", confidence=0.8):
            JumpManager.jump_to_bougu()
            Action.sell_loop_all_gomi_yoroi()
        Action.home()

    @staticmethod
    def sell_loop_all_gomi_yoroi():
        forbidden_range = 7
        lower_limit_yoroi = 0

        while True:
            result_souko = pyautogui.locateCenterOnScreen("souko.png", confidence=0.8)
            if result_souko:
                lower_limit_yoroi = result_souko[1]
                results_shino = list(pyautogui.locateAllOnScreen("shi-no.png", confidence=0.8))
                results_sell = list(pyautogui.locateAllOnScreen("sell.png", confidence=0.8))

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
            result_kouseki = pyautogui.locateCenterOnScreen("kouseki.png", confidence=0.8)
            if result_kouseki:
                lower_limit_kouseki = result_kouseki[1]
            results_shiro = list(pyautogui.locateAllOnScreen("kouseki-shiro.png", confidence=0.8))
            results_mizu = list(pyautogui.locateAllOnScreen("kouseki-mizu.png", confidence=0.8))
            results_hi = list(pyautogui.locateAllOnScreen("kouseki-hi.png", confidence=0.8))
            results_zya = list(pyautogui.locateAllOnScreen("kouseki-zya.png", confidence=0.8))
            results_radio = list(pyautogui.locateAllOnScreen("radio-button-2.png", confidence=0.8))

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
            results_shiro = list(pyautogui.locateAllOnScreen("kouseki-shiro.png", confidence=0.8))
            results_mizu = list(pyautogui.locateAllOnScreen("kouseki-mizu.png", confidence=0.8))
            results_hi = list(pyautogui.locateAllOnScreen("kouseki-hi.png", confidence=0.8))
            results_zya = list(pyautogui.locateAllOnScreen("kouseki-zya.png", confidence=0.8))
            results_radio = list(pyautogui.locateAllOnScreen("radio-button-2.png", confidence=0.8))

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
            if any(pyautogui.locateCenterOnScreen(f"{key}.png", confidence=0.8) for key in wait_keys):
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
    def collect_material(collect_mode, collect_yoroi, collect_various_kouseki):
        while True:
            Action.home()
            if collect_yoroi:
                Action.go_to_sell_all_gomi_yoroi()
            Action.go_to_sell_all_gomi_kouseki(collect_various_kouseki)

            loop_num = random.randint(375, 854)
            for _ in range(loop_num):
                pyautogui.press("home")
                time.sleep(0.5)
                if random.randint(1, 1000) > 995:
                    rest_time = random.randint(1, 300000) / 1000
                    print(f"約 {rest_time / 60:.2f} min の休憩に入ります。")
                    time.sleep(rest_time)

                if collect_mode == "Manomori":
                    Macro.step_manomori()
                elif collect_mode == "Saishu":
                    Macro.step_saishu()

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
        if pyautogui.locateCenterOnScreen("keitai.png", confidence=0.8):
            HandleRecaptcha.wait_for_captcha_ready()
            HandleRecaptcha.capture_screenshot("before")

            checks = [
                ("recaptcha-check", "recaptcha-success"),
                ("cloudflare-check", "cloudflare-success"),
                ("cloudflare-check-02", "cloudflare-success-02")
            ]

            for check_key, wait_key in checks:
                if pyautogui.locateCenterOnScreen(f"{check_key}.png", confidence=0.8):
                    HandleRecaptcha.check_recaptcha(check_key, wait_key)

            HandleRecaptcha.capture_screenshot("after")
            JumpManager.jump_to_madatuzukeru()
            HandleRecaptcha.capture_screenshot("negirai")
            JumpManager.jump_to_status()

