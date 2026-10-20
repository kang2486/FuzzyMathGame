
import re
import mysql.connector


def get_db_connection():
    """
    請將 app.py 目前使用的資料庫連線設定複製到這裡。
    密碼不要貼到聊天中。
    """
    return mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="Auag74123",
        database="fuzzy_math_game"
    )


def add_answer_blank(template):
    """在模板最後加入答案挖空，保留原有內容。"""

    if not template:
        return "{{blank:answer}}"

    if "{{blank:answer}}" in template:
        return template

    # 如果公式以問號結尾，將問號替換成答案挖空。
    if "?" in template:
        position = template.rfind("?")
        return (
            template[:position]
            + "{{blank:answer}}"
            + template[position + 1:]
        )

    # 沒有問號時，在原內容後面新增答案欄位。
    return template + r"\quad ={{blank:answer}}"


def main():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 讀取所有題目規格。
        cursor.execute("""
            SELECT spec_id, type_id, difficulty
            FROM question_spec
            ORDER BY type_id, difficulty
        """)
        specs = cursor.fetchall()

        if len(specs) != 100:
            raise ValueError(
                f"預期 100 種題目規格，實際查到 {len(specs)} 種。"
                "已停止執行，資料庫未修改。"
            )

        # 先檢查每種規格都有解題步驟，避免執行到一半才發現缺資料。
        for spec in specs:
            cursor.execute("""
                SELECT step_id
                FROM solution_step
                WHERE spec_id = %s
                ORDER BY step_order DESC, step_id DESC
                LIMIT 1
            """, (spec["spec_id"],))

            if cursor.fetchone() is None:
                raise ValueError(
                    f"{spec['spec_id']} 沒有解題步驟，"
                    "請先建立解題步驟後再執行。"
                )

        added_count = 0
        updated_count = 0
        skipped_count = 0

        for spec in specs:
            spec_id = spec["spec_id"]

            # 找出該規格最後一個步驟。
            cursor.execute("""
                SELECT
                    step_id,
                    step_order,
                    step_template,
                    step_latex_template
                FROM solution_step
                WHERE spec_id = %s
                ORDER BY step_order DESC, step_id DESC
                LIMIT 1
            """, (spec_id,))

            step = cursor.fetchone()

            # 檢查最後一步是否已經有答案挖空。
            latex = step["step_latex_template"] or ""
            text_template = step["step_template"] or ""

            already_blank = (
                "{{blank:answer}}" in latex
                or "{{blank:answer}}" in text_template
            )

            # 若沒有答案挖空，就加入公式與文字模板。
            if not already_blank:
                new_latex = add_answer_blank(latex)
                new_text = add_answer_blank(text_template)

                cursor.execute("""
                    UPDATE solution_step
                    SET step_latex_template = %s,
                        step_template = %s,
                        answer_template = %s
                    WHERE step_id = %s
                """, (
                    new_latex,
                    new_text,
                    "{{answer}}",
                    step["step_id"]
                ))
                updated_count += 1
            else:
                skipped_count += 1

            # 確認這一步是否已有 answer 的挖空規則。
            cursor.execute("""
                SELECT blank_id
                FROM blank_rule
                WHERE spec_id = %s
                  AND step_order = %s
                  AND blank_key = 'answer'
                LIMIT 1
            """, (spec_id, step["step_order"]))

            existing_blank = cursor.fetchone()

            if existing_blank:
                # 保留既有規則，只修正標準答案模板。
                cursor.execute("""
                    UPDATE blank_rule
                    SET correct_answer_template = %s,
                        target_expression = %s
                    WHERE blank_id = %s
                """, (
                    "{{answer}}",
                    "最終答案",
                    existing_blank["blank_id"]
                ))
            else:
                cursor.execute("""
                    INSERT INTO blank_rule (
                        spec_id,
                        step_order,
                        blank_key,
                        target_expression,
                        correct_answer_template,
                        answer_type,
                        blank_level,
                        hint
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    spec_id,
                    step["step_order"],
                    "answer",
                    "最終答案",
                    "{{answer}}",
                    "EXPRESSION",
                    1,
                    "完成解題步驟後，輸入最終答案。"
                ))
                added_count += 1

            print(
                f"[完成] {spec_id}："
                f"最後步驟 = {step['step_order']}"
            )

        # 所有規格處理成功後才提交。
        connection.commit()

        print("\n========== 執行結果 ==========")
        print(f"題目規格總數：{len(specs)}")
        print(f"新增挖空規則：{added_count}")
        print(f"更新步驟模板：{updated_count}")
        print(f"原本已有挖空：{skipped_count}")
        print("資料已成功寫入 MySQL。")

    except Exception:
        connection.rollback()
        print("執行失敗，已回復本次資料庫交易。")
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
