import cv2
import numpy as np
import os
import pyautogui
from AutoFFB import ImageRecognizer


def test_locate_and_visualize(key, output_filename="output.png"):
    params = ImageRecognizer.IMAGE_PARAMS.get(key)
    if not params:
        print(f"⚠️ '{key}' の画像パラメータが登録されていません。")
        return

    filename = os.path.join(ImageRecognizer.IMAGE_FOLDER, params["filename"])
    region = params["region"]
    confidence = params["confidence"]

    # スクリーンショットを取得
    screenshot = np.array(pyautogui.screenshot(region=region))
    screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)

    # 画像テンプレートを読み込む
    template = cv2.imread(filename, cv2.IMREAD_COLOR)
    if template is None:
        print(f"⚠️ '{filename}' の画像が見つかりませんでした。")
        return

    # テンプレートマッチング
    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    loc = np.where(result >= confidence)
    h, w = template.shape[:2]

    # 認識結果を描画
    used_positions = set()
    for pt in zip(*loc[::-1]):
        match_confidence = result[pt[1], pt[0]]
        cv2.rectangle(screenshot, pt, (pt[0] + w, pt[1] + h), (0, 0, 255), 2)

        # 近い座標に重複して描画しないように調整
        text_x, text_y = pt[0], pt[1] - 5
        while (text_x, text_y) in used_positions:
            text_y += 15  # 重ならないように調整
        used_positions.add((text_x, text_y))

        cv2.putText(screenshot, f"{match_confidence:.2f}", (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)

    # 画像を保存
    cv2.imwrite(output_filename, screenshot)
    print(f"✅ '{output_filename}' に結果を保存しました。")


# テスト実行
if __name__ == "__main__":
    test_key = "kouseki-shiro"  # テストしたいキーを指定
    test_locate_and_visualize(test_key, test_key+"_result.png")
