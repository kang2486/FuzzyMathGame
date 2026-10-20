
"""
fuzzy_difficulty.py

FuzzyMathGame - 第二套模糊邏輯
功能：
1. 輸入玩家能力值（0～100）
2. 計算五個模糊集合的隸屬度
3. 將隸屬度正規化成選題機率
4. 隨機選擇下一題難度（1～5）
"""

import random


# =====================================================
# 1. 能力值範圍
# =====================================================

MIN_ABILITY = 0
MAX_ABILITY = 100


# =====================================================
# 2. 隸屬函數
# =====================================================

def left_shoulder(x, a, b):
    """
    左肩形隸屬函數。

    x <= a：隸屬度為 1
    a < x < b：隸屬度線性下降
    x >= b：隸屬度為 0

    例如 VL：left_shoulder(x, 0, 25)
    """

    if x <= a:
        return 1.0

    if x >= b:
        return 0.0

    return (b - x) / (b - a)


def triangle(x, a, b, c):
    """
    三角形隸屬函數。

    x <= a 或 x >= c：隸屬度為 0
    x == b：隸屬度為 1
    其他位置：依照線性比例計算
    """

    if x <= a or x >= c:
        return 0.0

    if x == b:
        return 1.0

    if x < b:
        return (x - a) / (b - a)

    return (c - x) / (c - b)


def right_shoulder(x, a, b):
    """
    右肩形隸屬函數。

    x <= a：隸屬度為 0
    a < x < b：隸屬度線性上升
    x >= b：隸屬度為 1

    例如 VH：right_shoulder(x, 75, 100)
    """

    if x <= a:
        return 0.0

    if x >= b:
        return 1.0

    return (x - a) / (b - a)


# =====================================================
# 3. 計算五個能力值模糊集合的隸屬度
# =====================================================

def calculate_memberships(ability):
    """
    輸入能力值，回傳五種難度的隸屬度。

    VL：左肩形 (0, 25)
    L ：三角形 (0, 25, 50)
    M ：三角形 (25, 50, 75)
    H ：三角形 (50, 75, 100)
    VH：右肩形 (75, 100)
    """

    ability = float(ability)

    if not MIN_ABILITY <= ability <= MAX_ABILITY:
        raise ValueError("能力值必須介於 0～100。")

    memberships = {
        1: left_shoulder(ability, 0, 25),
        2: triangle(ability, 0, 25, 50),
        3: triangle(ability, 25, 50, 75),
        4: triangle(ability, 50, 75, 100),
        5: right_shoulder(ability, 75, 100),
    }

    return memberships


# =====================================================
# 4. 將隸屬度正規化成機率
# =====================================================

def calculate_probabilities(ability):
    """
    將各難度的隸屬度轉換成選題機率。

    P(Di) = mu(Di) / 所有隸屬度的總和
    """

    memberships = calculate_memberships(ability)

    total = sum(memberships.values())

    if total <= 0:
        raise ValueError("所有難度的隸屬度皆為 0，無法選題。")

    probabilities = {
        difficulty: membership / total
        for difficulty, membership in memberships.items()
    }

    return probabilities


# =====================================================
# 5. 隨機選擇下一題難度
# =====================================================

def select_difficulty(ability):
    """
    根據能力值與正規化後的機率，選擇難度 1～5。

    回傳：
        difficulty：選出的難度
        probabilities：各難度的選題機率
        memberships：各難度的原始隸屬度
    """

    memberships = calculate_memberships(ability)
    probabilities = calculate_probabilities(ability)

    difficulty_list = list(probabilities.keys())
    probability_list = list(probabilities.values())

    selected_difficulty = random.choices(
        difficulty_list,
        weights=probability_list,
        k=1
    )[0]

    return {
        "ability": float(ability),
        "memberships": memberships,
        "probabilities": probabilities,
        "difficulty": selected_difficulty,
    }


# =====================================================
# 6. 測試程式
# =====================================================

if __name__ == "__main__":

    test_abilities = [10, 25, 40, 50, 60, 65, 75, 90]

    for ability in test_abilities:

        result = select_difficulty(ability)

        print("=" * 50)
        print(f"目前能力值：{ability}")

        print("各難度隸屬度：")
        for difficulty, membership in result["memberships"].items():
            print(
                f"難度 {difficulty}："
                f"{membership:.2f}"
            )

        print("各難度選題機率：")
        for difficulty, probability in result["probabilities"].items():
            print(
                f"難度 {difficulty}："
                f"{probability:.0%}"
            )

        print(f"本次選出的難度：{result['difficulty']}")
