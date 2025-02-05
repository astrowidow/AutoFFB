import cv2
import pyautogui
import numpy as np
import os
from AutoFFB import ImageRecognizer


def test_image_recognition(key):
    params = ImageRecognizer.IMAGE_PARAMS.get(key)
    if not params:
        print(f"⚠️ '{key}' の画像パラメータが登録されていません。")
        return

    filename = params["filename"]
    region = params["region"]
    confidence = params["confidence"]

    screenshot = pyautogui.screenshot(region=region)
    screenshot = np.array(screenshot)
    screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)

    try:
        locations = list(pyautogui.locateAllOnScreen(filename, confidence=confidence, region=region))
    except pyautogui.ImageNotFoundException:
        print(f"⚠️ '{key}' の画像が見つかりませんでした。スクリーンショットを保存します。")
        locations = []
    except Exception as e:
        print(f"⚠️ 予期しないエラー: {e}")
        locations = []

    if locations:
        for loc in locations:
            x, y, width, height = loc.left, loc.top, loc.width, loc.height
            cv2.rectangle(screenshot, (x, y), (x + width, y + height), (0, 0, 255), 2)
            cv2.putText(screenshot, key, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    output_filename = f"test_result_{key}.png"
    cv2.imwrite(output_filename, screenshot)
    print(f"📸 テスト結果を保存しました: {output_filename}")


# テスト実行例
test_image_recognition("champ")  # champキーをテスト