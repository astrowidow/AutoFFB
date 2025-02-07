import requests
import socket
import platform

# Discord Webhook URL（取得したものを設定）
WEBHOOK_URL = ""


def get_machine_info():
    """
    現在のマシンの情報を取得する
    """
    host_name = socket.gethostname()  # ホスト名
    user_name = platform.node()  # ユーザー名
    os_info = platform.system() + " " + platform.release()  # OS情報
    ip_address = socket.gethostbyname(socket.gethostname())  # ローカルIP

    machine_info = f"📡 **投稿者情報**\n"
    machine_info += f"🖥 **ホスト名:** {host_name}\n"
    machine_info += f"👤 **ユーザー名:** {user_name}\n"
    machine_info += f"💻 **OS:** {os_info}\n"
    machine_info += f"🌍 **IP:** {ip_address}\n"

    return machine_info


def send_discord_message(message: str):
    """
    Discordに投稿者情報付きでメッセージを送信
    """
    machine_info = get_machine_info()
    full_message = f"{message}\n\n{machine_info}"

    data = {"content": full_message}
    response = requests.post(WEBHOOK_URL, json=data)

    if response.status_code == 204:
        print("✅ メッセージ送信成功！")
    else:
        print(f"⚠️ エラー: {response.status_code}")
        print(response.text)


def send_discord_image(image_path: str, caption: str = ""):
    """
    Discordに投稿者情報付きで画像を送信
    """
    machine_info = get_machine_info()
    full_caption = f"{caption}\n\n{machine_info}"

    with open(image_path, "rb") as image_file:
        files = {"file": image_file}
        data = {"content": full_caption}
        response = requests.post(WEBHOOK_URL, data=data, files=files)

    if response.status_code == 204:
        print("✅ 画像送信成功！")
    else:
        print(f"⚠️ エラー: {response.status_code}")
        print(response.text)


# 🔹 テスト実行
if __name__ == "__main__":
    send_discord_message("📢 これは投稿者情報付きのテストメッセージです！")
    send_discord_image("kouseki-shiro_result.png", "📷 画像付きメッセージ！")