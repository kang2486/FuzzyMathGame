
import requests

BASE_URL = "http://127.0.0.1:5000"

QUESTION_TYPES = [
    f"F{i:02d}" for i in range(1, 21)
]

DIFFICULTIES = [1, 2, 3, 4, 5]


def test_question(type_id, difficulty):
    """測試指定題型與難度能否成功生成題目。"""

    url = f"{BASE_URL}/api/questions/generate/{type_id}"

    try:
        response = requests.get(
            url,
            params={"difficulty": difficulty},
            timeout=15
        )
    except requests.RequestException as error:
        return False, f"連線失敗：{error}"

    if response.status_code != 200:
        return False, (
            f"HTTP {response.status_code}："
            f"{response.text[:300]}"
        )

    try:
        data = response.json()
    except ValueError:
        return False, "回應不是有效的 JSON"

    if data.get("status") == "error" or data.get("error"):
        return False, str(data)[:300]

    # 兼容不同版本 API 的題目欄位名稱
    question = (
        data.get("question_text")
        or data.get("question")
    )

    if not question:
        return False, (
            "API 回應成功，但找不到題目文字。"
            f"回應內容：{str(data)[:300]}"
        )

    return True, question


def main():
    print("=" * 60)
    print("F01～F20 × D1～D5 全部 100 種規格批次測試")
    print("=" * 60)

    success_count = 0
    failure_count = 0
    failures = []

    for type_id in QUESTION_TYPES:
        for difficulty in DIFFICULTIES:
            success, result = test_question(
                type_id,
                difficulty
            )

            label = f"{type_id} D{difficulty}"

            if success:
                success_count += 1
                print(f"[成功] {label}：{result}")
            else:
                failure_count += 1
                failures.append((label, result))
                print(f"[失敗] {label}：{result}")

    total = len(QUESTION_TYPES) * len(DIFFICULTIES)

    print("\n" + "=" * 60)
    print(f"測試總數：{total}")
    print(f"成功：{success_count}")
    print(f"失敗：{failure_count}")
    print(
        f"成功率：{success_count / total * 100:.1f}%"
    )
    print("=" * 60)

    if failures:
        print("\n以下規格需要修正：")

        for label, reason in failures:
            print(f"\n{label}")
            print(f"原因：{reason}")
    else:
        print("\n全部 100 種規格皆成功生成題目。")


if __name__ == "__main__":
    main()
