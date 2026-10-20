
"""
FuzzyMathGame - fuzzy_ability.py

功能：
1. 使用四個輸入變數進行模糊推論
2. 答對：能力值增加 +1 ~ +5
3. 答錯：能力值扣除 0 ~ -5，不設定扣分保底
4. 答對時，超過標準時間不給時間額外獎勵
5. 答錯時，越快答錯，時間懲罰越重
6. 不依賴 numpy 或其他第三方套件

輸入：
    remaining_hp : 剩餘 HP，0~100
    hint_count   : 使用提示次數，0~5
    difficulty   : 題目難度，1~5
    elapsed_time : 作答秒數，必須 >= 0
    is_correct   : 是否答對，True / False

輸出：
    ability_change : 能力值增減幅度
    new_ability    : 更新後的能力值
    details        : 計算細節
"""

from itertools import product


# ============================================================
# 1. 基本設定
# ============================================================

STANDARD_TIMES = {
    1: 60,
    2: 90,
    3: 120,
    4: 150,
    5: 180,
}

ABILITY_MIN = 0
ABILITY_MAX = 100

CORRECT_BASE_GAIN = 1.0
CORRECT_MAX_GAIN = 5.0
WRONG_MAX_PENALTY = 5.0

EPSILON = 1e-9


# ============================================================
# 2. 隸屬函數
# ============================================================

def triangular(x, a, b, c):
    """三角形隸屬函數。"""
    if x < a or x > c:
        return 0.0

    if x == b:
        return 1.0

    if x < b:
        return (x - a) / (b - a) if b != a else 1.0

    return (c - x) / (c - b) if c != b else 1.0


def left_shoulder(x, a, b):
    """左肩型：x <= a 時為 1，x >= b 時為 0。"""
    if x <= a:
        return 1.0

    if x >= b:
        return 0.0

    return (b - x) / (b - a)


def right_shoulder(x, a, b):
    """右肩型：x <= a 時為 0，x >= b 時為 1。"""
    if x <= a:
        return 0.0

    if x >= b:
        return 1.0

    return (x - a) / (b - a)


# ============================================================
# 3. HP 隸屬函數：剩餘 HP
# ============================================================

def fuzzify_hp(hp):
    """
    HP 使用剩餘值。
    低 HP：生命值低。
    中 HP：生命值中等。
    高 HP：生命值高。
    """
    return {
        "low": left_shoulder(hp, 25, 50),
        "medium": triangular(hp, 25, 50, 75),
        "high": right_shoulder(hp, 50, 75),
    }


# ============================================================
# 4. MP 隸屬函數：提示使用次數
# ============================================================

def fuzzify_mp(count):
    """
    提示最多使用 5 次。
    無：0 次。
    少：0~2 次附近。
    中：2~4 次。
    多：4~5 次附近。
    """
    return {
        "none": left_shoulder(count, 0, 1),
        "low": triangular(count, 0, 2, 4),
        "medium": triangular(count, 1, 3, 5),
        "high": right_shoulder(count, 4, 5),
    }


# ============================================================
# 5. 難度隸屬函數：VL、L、M、H、VH
# ============================================================

def fuzzify_difficulty(difficulty):
    """
    VL：1 -> 1，2 -> 0
    L ：(1,0), (2,1), (3,0)
    M ：(2,0), (3,1), (4,0)
    H ：(3,0), (4,1), (5,0)
    VH：4 -> 0，5 -> 1
    """
    return {
        "VL": left_shoulder(difficulty, 1, 2),
        "L": triangular(difficulty, 1, 2, 3),
        "M": triangular(difficulty, 2, 3, 4),
        "H": triangular(difficulty, 3, 4, 5),
        "VH": right_shoulder(difficulty, 4, 5),
    }


# ============================================================
# 6. 時間隸屬函數
# ============================================================

def fuzzify_time(elapsed_time, standard_time):
    """
    將實際時間轉換為標準時間使用比例。

    r = elapsed_time / standard_time

    快：0~40%
    中：25~75%
    慢：60~100%

    超過標準時間後，slow = 1。
    """
    ratio = elapsed_time / standard_time

    if ratio >= 1:
        return {
            "fast": 0.0,
            "medium": 0.0,
            "slow": 1.0,
        }

    return {
        "fast": left_shoulder(ratio, 0.0, 0.4),
        "medium": triangular(ratio, 0.25, 0.5, 0.75),
        "slow": right_shoulder(ratio, 0.6, 1.0),
    }


# ============================================================
# 7. 通用 Sugeno 型模糊推論
# ============================================================

def sugeno_inference(membership_sets, consequent_values):
    """
    membership_sets:
        各輸入變數的隸屬度字典列表。

    consequent_values:
        每一條規則對應的輸出值。

    規則觸發強度：
        firing_strength = 所有前件隸屬度的乘積。

    最終輸出：
        各規則輸出值的加權平均。
    """
    names = [list(group.keys()) for group in membership_sets]

    weighted_sum = 0.0
    total_weight = 0.0

    for combination in product(*names):
        strength = 1.0

        for group, label in zip(membership_sets, combination):
            strength *= group[label]

        if strength <= 0:
            continue

        output = consequent_values(combination)

        weighted_sum += strength * output
        total_weight += strength

    if total_weight <= EPSILON:
        return 0.0

    return weighted_sum / total_weight


# ============================================================
# 8. 答對規則
# ============================================================

def calculate_correct_gain(
    remaining_hp,
    hint_count,
    difficulty,
    elapsed_time,
    standard_time,
):
    """
    答對：
        基礎 +1
        額外獎勵最高 +4

    額外獎勵權重：
        時間 50%
        提示使用 25%
        剩餘 HP 15%
        難度 10%

    超過標準時間：
        額外時間獎勵直接為 0。
    """

    hp_sets = fuzzify_hp(remaining_hp)
    mp_sets = fuzzify_mp(hint_count)
    difficulty_sets = fuzzify_difficulty(difficulty)
    time_sets = fuzzify_time(elapsed_time, standard_time)

    # 各集合轉換成 0~1 的表現分數
    hp_score = {
        "low": 0.0,
        "medium": 0.5,
        "high": 1.0,
    }

    mp_score = {
        "none": 1.0,
        "low": 0.75,
        "medium": 0.4,
        "high": 0.0,
    }

    difficulty_score = {
        "VL": 0.0,
        "L": 0.25,
        "M": 0.5,
        "H": 0.75,
        "VH": 1.0,
    }

    time_score = {
        "fast": 1.0,
        "medium": 0.5,
        "slow": 0.0,
    }

    def rule_output(rule):
        hp, mp, diff, time = rule

        return (
            0.15 * hp_score[hp]
            + 0.25 * mp_score[mp]
            + 0.10 * difficulty_score[diff]
            + 0.50 * time_score[time]
        )

    performance = sugeno_inference(
        [
            hp_sets,
            mp_sets,
            difficulty_sets,
            time_sets,
        ],
        rule_output,
    )

    # 超過標準時間，不提供額外時間獎勵。
    if elapsed_time >= standard_time:
        performance = 0.0

    # 額外獎勵 0~4，加上保底 1。
    gain = CORRECT_BASE_GAIN + 4.0 * performance

    return min(CORRECT_MAX_GAIN, max(CORRECT_BASE_GAIN, gain))


# ============================================================
# 9. 答錯規則
# ============================================================

def calculate_wrong_penalty(
    remaining_hp,
    hint_count,
    difficulty,
    elapsed_time,
    standard_time,
):
    """
    答錯時的懲罰權重：
        時間 55%
        提示使用 25%
        剩餘 HP 12%
        難度 8%

    時間越短，懲罰越重。
    使用提示越多，懲罰越重。
    剩餘 HP 越低，懲罰稍微提高。
    難度越高，懲罰稍微提高。

    不設扣分保底，最大扣 5。
    """

    hp_sets = fuzzify_hp(remaining_hp)
    mp_sets = fuzzify_mp(hint_count)
    difficulty_sets = fuzzify_difficulty(difficulty)
    time_sets = fuzzify_time(elapsed_time, standard_time)

    hp_penalty = {
        "low": 1.0,
        "medium": 0.5,
        "high": 0.0,
    }

    mp_penalty = {
        "none": 0.0,
        "low": 0.25,
        "medium": 0.65,
        "high": 1.0,
    }

    difficulty_penalty = {
        "VL": 0.0,
        "L": 0.25,
        "M": 0.5,
        "H": 0.75,
        "VH": 1.0,
    }

    time_penalty = {
        "fast": 1.0,
        "medium": 0.5,
        "slow": 0.0,
    }

    def rule_output(rule):
        hp, mp, diff, time = rule

        return (
            0.12 * hp_penalty[hp]
            + 0.25 * mp_penalty[mp]
            + 0.08 * difficulty_penalty[diff]
            + 0.55 * time_penalty[time]
        )

    penalty_ratio = sugeno_inference(
        [
            hp_sets,
            mp_sets,
            difficulty_sets,
            time_sets,
        ],
        rule_output,
    )

    penalty = WRONG_MAX_PENALTY * penalty_ratio

    # 不設最低扣分保底，只限制最大扣分為 5。
    return min(WRONG_MAX_PENALTY, max(0.0, penalty))


# ============================================================
# 10. 對外使用的主要函式
# ============================================================

def calculate_ability_change(
    remaining_hp,
    hint_count,
    difficulty,
    elapsed_time,
    is_correct,
    current_ability,
):
    """
    計算能力值變動，並更新能力值。

    回傳 dict：
        ability_change：有正負號的能力值變動
        new_ability：更新後的能力值
        details：詳細資訊
    """

    # ---------- 輸入驗證 ----------

    if not isinstance(remaining_hp, (int, float)):
        raise TypeError("remaining_hp 必須是數值")

    if remaining_hp not in (0, 25, 50, 75, 100):
        raise ValueError("remaining_hp 必須為 0、25、50、75、100")

    if not isinstance(hint_count, int) or isinstance(hint_count, bool):
        raise TypeError("hint_count 必須是整數")

    if not 0 <= hint_count <= 5:
        raise ValueError("hint_count 必須介於 0~5")

    if difficulty not in STANDARD_TIMES:
        raise ValueError("difficulty 必須介於 1~5")

    if elapsed_time < 0:
        raise ValueError("elapsed_time 不可小於 0")

    if not isinstance(is_correct, bool):
        raise TypeError("is_correct 必須是 True 或 False")

    if not isinstance(current_ability, (int, float)):
        raise TypeError("current_ability 必須是數值")

    if not ABILITY_MIN <= current_ability <= ABILITY_MAX:
        raise ValueError("current_ability 必須介於 0~100")

    standard_time = STANDARD_TIMES[difficulty]

    # ---------- Fuzzy 推論 ----------

    if is_correct:
        magnitude = calculate_correct_gain(
            remaining_hp,
            hint_count,
            difficulty,
            elapsed_time,
            standard_time,
        )

        change = magnitude

    else:
        magnitude = calculate_wrong_penalty(
            remaining_hp,
            hint_count,
            difficulty,
            elapsed_time,
            standard_time,
        )

        change = -magnitude

    # ---------- 更新能力值 ----------

    new_ability = current_ability + change

    new_ability = max(
        ABILITY_MIN,
        min(ABILITY_MAX, new_ability),
    )

    # 回傳實際變動，避免能力值已到上下限時數字不一致。
    actual_change = new_ability - current_ability

    return {
        "ability_change": round(actual_change, 2),
        "new_ability": round(new_ability, 2),
        "details": {
            "is_correct": is_correct,
            "remaining_hp": remaining_hp,
            "hint_count": hint_count,
            "difficulty": difficulty,
            "elapsed_time": elapsed_time,
            "standard_time": standard_time,
            "time_ratio": round(
                elapsed_time / standard_time, 4
            ),
            "magnitude": round(magnitude, 2),
        },
    }


# ============================================================
# 11. 單獨測試
# ============================================================

if __name__ == "__main__":

    test_cases = [
        {
            "name": "答對、快速、無提示、高難度",
            "remaining_hp": 100,
            "hint_count": 0,
            "difficulty": 5,
            "elapsed_time": 30,
            "is_correct": True,
            "current_ability": 50,
        },
        {
            "name": "答對、超過標準時間",
            "remaining_hp": 75,
            "hint_count": 2,
            "difficulty": 3,
            "elapsed_time": 150,
            "is_correct": True,
            "current_ability": 50,
        },
        {
            "name": "答錯、快速、使用很多提示",
            "remaining_hp": 50,
            "hint_count": 4,
            "difficulty": 4,
            "elapsed_time": 15,
            "is_correct": False,
            "current_ability": 50,
        },
        {
            "name": "答錯、花較長時間思考",
            "remaining_hp": 75,
            "hint_count": 1,
            "difficulty": 2,
            "elapsed_time": 85,
            "is_correct": False,
            "current_ability": 50,
        },
    ]

    for case in test_cases:
        name = case.pop("name")
        result = calculate_ability_change(**case)

        print("=" * 50)
        print(name)
        print("能力值變動：", result["ability_change"])
        print("更新後能力值：", result["new_ability"])
        print("詳細資訊：", result["details"])
