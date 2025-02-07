import random
from AutoFFB import *

screen_width = 1920
screen_height = 1080
num_tests = 10
errors = 0

for i in range(num_tests):
    start = (random.randint(0, screen_width), random.randint(0, screen_height))
    end = (random.randint(0, screen_width), random.randint(0, screen_height))
    duration = random.uniform(1.0, 3.0)

    try:
        HandleRecaptcha.human_like_mouse_move(start, end, duration)
        print(f"Test {i + 1}/{num_tests}: Passed")
    except Exception as e:
        print(f"Test {i + 1}/{num_tests}: Failed - {e}")
        errors += 1

    time.sleep(0.1)  # 負荷を下げるための短い待機時間

print(f"\nTest completed: {num_tests} cases run, {errors} errors ecncountered.")