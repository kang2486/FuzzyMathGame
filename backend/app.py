
from flask import Flask, jsonify, send_from_directory
import mysql.connector
import os
import random
import json


# ==========================================
# 1. 專案路徑與 Flask 設定
# ==========================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

app = Flask(
    __name__,
    static_folder=BASE_DIR,
    static_url_path="/static"
)

print("===== 專案路徑檢查 =====")
print("BASE_DIR =", BASE_DIR)
print(
    "index.html exists =",
    os.path.isfile(os.path.join(BASE_DIR, "index.html"))
)
print(
    "CSS exists =",
    os.path.isfile(os.path.join(BASE_DIR, "css", "style.css"))
)
print(
    "JS exists =",
    os.path.isfile(os.path.join(BASE_DIR, "js", "main.js"))
)


# ==========================================
# 2. 資料庫連線
# ==========================================

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="請輸入你的MYSQL根密碼",
        database="fuzzy_math_game"
    )


# ==========================================
# 3. 首頁
# ==========================================

@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


# ==========================================
# 4. API 測試
# ==========================================

@app.route("/api/test")
def test_api():
    return jsonify({
        "message": "API is working!",
        "project": "FuzzyMathGame"
    })


# ==========================================
# 5. 取得資料庫中的全部題目
# ==========================================

@app.route("/api/questions")
def get_questions():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                q.question_id,
                t.type_name,
                t.chapter,
                q.difficulty,
                q.latex_expression,
                q.parameters
            FROM question_bank AS q
            JOIN question_type AS t
                ON q.type_id = t.question_type_id
            ORDER BY q.question_id
        """

        cursor.execute(sql)
        questions = cursor.fetchall()

        for question in questions:
            if isinstance(question["parameters"], str):
                question["parameters"] = json.loads(
                    question["parameters"]
                )

        return jsonify(questions)

    except mysql.connector.Error:
        app.logger.exception("MySQL 查詢失敗")

        return jsonify({
            "error": "資料庫查詢失敗"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# ==========================================
# 6. 根據題型取得題目
# ==========================================

@app.route("/api/questions/<type_id>")
def get_questions_by_type(type_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                q.question_id,
                q.type_id,
                t.type_name,
                t.chapter,
                q.difficulty,
                q.latex_expression,
                q.parameters
            FROM question_bank AS q
            JOIN question_type AS t
                ON q.type_id = t.question_type_id
            WHERE q.type_id = %s
            ORDER BY q.question_id
        """

        cursor.execute(sql, (type_id,))
        questions = cursor.fetchall()

        for question in questions:
            if isinstance(question["parameters"], str):
                question["parameters"] = json.loads(
                    question["parameters"]
                )

        return jsonify(questions)

    except mysql.connector.Error:
        app.logger.exception("MySQL 查詢失敗")

        return jsonify({
            "error": "資料庫查詢失敗"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# ==========================================
# 7. 取得指定題型的參數規則
# ==========================================

@app.route("/api/parameters/<type_id>")
def get_parameters(type_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                parameter_name,
                default_value,
                min_value,
                max_value
            FROM parameter_rule
            WHERE type_id = %s
            ORDER BY parameter_name
        """

        cursor.execute(sql, (type_id,))
        parameters = cursor.fetchall()

        return jsonify(parameters)

    except mysql.connector.Error:
        app.logger.exception("參數規則查詢失敗")

        return jsonify({
            "error": "參數規則查詢失敗"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# ==========================================
# 8. 多項式格式化
# ==========================================

def format_polynomial(a, b, c, d):
    """將三次多項式轉成 LaTeX 格式。"""

    terms = [
        (a, "x", 3),
        (b, "x", 2),
        (c, "x", 1),
        (d, "", 0)
    ]

    result = ""

    for coefficient, variable, power in terms:
        if coefficient == 0:
            continue

        sign = "-" if coefficient < 0 else "+"
        value = abs(coefficient)

        if power == 0:
            term = str(value)

        elif power == 1:
            term = f"{value}{variable}"

        elif value == 1:
            term = f"{variable}^{{{power}}}"

        else:
            term = f"{value}{variable}^{{{power}}}"

        if result == "":
            result = (
                ("-" if coefficient < 0 else "")
                + term
            )
        else:
            result += sign + term

    return "f(x)=" + result


# ==========================================
# 9. 隨機生成多項式微分題目
# ==========================================

@app.route("/api/questions/generate/<type_id>")
def generate_question(type_id):
    connection = None
    cursor = None

    try:
        if type_id != "T001":
            return jsonify({
                "error": "目前只支援 T001 多項式微分"
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                parameter_name,
                min_value,
                max_value
            FROM parameter_rule
            WHERE type_id = %s
        """

        cursor.execute(sql, (type_id,))
        rules = cursor.fetchall()

        if not rules:
            return jsonify({
                "error": "找不到這個題型的參數規則"
            }), 404

        parameters = {}

        for rule in rules:
            name = rule["parameter_name"]
            minimum = int(rule["min_value"])
            maximum = int(rule["max_value"])

            if minimum > maximum:
                return jsonify({
                    "error": f"參數 {name} 的範圍設定錯誤"
                }), 500

            parameters[name] = random.randint(
                minimum,
                maximum
            )

        # 三次項係數不可為 0
        if parameters.get("a", 0) == 0:
            a_rule = next(
                (
                    rule for rule in rules
                    if rule["parameter_name"] == "a"
                ),
                None
            )

            if a_rule is None:
                return jsonify({
                    "error": "找不到三次項係數規則"
                }), 500

            valid_a = [
                value
                for value in range(
                    int(a_rule["min_value"]),
                    int(a_rule["max_value"]) + 1
                )
                if value != 0
            ]

            if not valid_a:
                return jsonify({
                    "error": "三次項係數範圍不能只有 0"
                }), 500

            parameters["a"] = random.choice(valid_a)

        required = ["a", "b", "c", "d"]

        if not all(name in parameters for name in required):
            return jsonify({
                "error": "T001 缺少必要的參數規則"
            }), 500

        a = parameters["a"]
        b = parameters["b"]
        c = parameters["c"]
        d = parameters["d"]

        expression = format_polynomial(a, b, c, d)

        return jsonify({
            "type_id": type_id,
            "type_name": "多項式微分",
            "difficulty": 1,
            "latex_expression": expression,
            "parameters": parameters
        })

    except mysql.connector.Error:
        app.logger.exception("隨機出題時資料庫查詢失敗")

        return jsonify({
            "error": "資料庫查詢失敗"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# ==========================================
# 10. 取得指定題型與難度的解題步驟
# ==========================================

@app.route("/api/solution-steps/<type_id>/<int:difficulty>")
def get_solution_steps(type_id, difficulty):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                step_id,
                type_id,
                difficulty,
                step_order,
                step_description,
                step_template,
                answer_template
            FROM solution_step
            WHERE type_id = %s
              AND difficulty = %s
            ORDER BY step_order
        """

        cursor.execute(sql, (type_id, difficulty))
        steps = cursor.fetchall()

        if not steps:
            return jsonify({
                "error": "找不到這個題型與難度的解題步驟"
            }), 404

        return jsonify({
            "type_id": type_id,
            "difficulty": difficulty,
            "total_steps": len(steps),
            "steps": steps
        })

    except mysql.connector.Error:
        app.logger.exception("解題步驟查詢失敗")

        return jsonify({
            "error": "解題步驟查詢失敗"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# ==========================================
# 11. 隨機產生題目與對應解題步驟
# ==========================================

@app.route("/api/questions/generate-with-steps/<type_id>")
def generate_question_with_steps(type_id):
    connection = None
    cursor = None

    try:
        if type_id != "T001":
            return jsonify({
                "error": "目前只支援 T001 多項式微分"
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # 1. 讀取參數規則
        cursor.execute("""
            SELECT
                parameter_name,
                min_value,
                max_value
            FROM parameter_rule
            WHERE type_id = %s
        """, (type_id,))

        rules = cursor.fetchall()

        if not rules:
            return jsonify({
                "error": "找不到題目參數規則"
            }), 404

        # 2. 隨機產生參數
        parameters = {}

        for rule in rules:
            name = rule["parameter_name"]
            minimum = int(rule["min_value"])
            maximum = int(rule["max_value"])

            if minimum > maximum:
                return jsonify({
                    "error": f"參數 {name} 的範圍設定錯誤"
                }), 500

            parameters[name] = random.randint(
                minimum,
                maximum
            )

        # 3. 確認必要參數完整
        required = ["a", "b", "c", "d"]

        if not all(name in parameters for name in required):
            return jsonify({
                "error": "T001 缺少必要的參數規則"
            }), 500

        # 三次項係數不可為 0
        if parameters["a"] == 0:
            a_rule = next(
                (
                    rule for rule in rules
                    if rule["parameter_name"] == "a"
                ),
                None
            )

            if a_rule is None:
                return jsonify({
                    "error": "找不到三次項係數規則"
                }), 500

            valid_values = [
                number
                for number in range(
                    int(a_rule["min_value"]),
                    int(a_rule["max_value"]) + 1
                )
                if number != 0
            ]

            if not valid_values:
                return jsonify({
                    "error": "三次項係數範圍不能只有 0"
                }), 500

            parameters["a"] = random.choice(valid_values)

        a = parameters["a"]
        b = parameters["b"]
        c = parameters["c"]
        d = parameters["d"]

        # 4. 產生題目
        expression = format_polynomial(a, b, c, d)

        # 5. 取得資料庫中的解題步驟
        cursor.execute("""
            SELECT
                step_order,
                step_description,
                step_template
            FROM solution_step
            WHERE type_id = %s
              AND difficulty = %s
            ORDER BY step_order
        """, (type_id, 1))

        step_rules = cursor.fetchall()

        if not step_rules:
            return jsonify({
                "error": "找不到這個難度的解題步驟"
            }), 404

        # 6. 計算微分過程
        derivative_cubic = format_polynomial(
            0, 3 * a, 0, 0
        )[5:]

        derivative_linear = format_polynomial(
            0, 0, 2 * b, c
        )[5:]

        final_answer = format_polynomial(
            0, 3 * a, 2 * b, c
        ).replace("f(x)=", "f'(x)=")

        steps = []

        for rule in step_rules:
            order = rule["step_order"]

            if order == 1:
                content = (
                    f"\\frac{{d}}{{dx}}"
                    f"\\left({a}x^3\\right)"
                    f"={derivative_cubic}"
                )

            elif order == 2:
                content = (
                    f"\\frac{{d}}{{dx}}"
                    f"\\left({b}x^2+({c})x\\right)"
                    f"={derivative_linear}"
                )

            elif order == 3:
                content = (
                    f"\\frac{{d}}{{dx}}({d})=0"
                    f",\\quad {final_answer}"
                )

            else:
                content = "此步驟的計算規則尚未實作"

            steps.append({
                "step_order": order,
                "step_description": rule["step_description"],
                "content": content
            })

        # 7. 回傳題目與步驟
        return jsonify({
            "type_id": type_id,
            "type_name": "多項式微分",
            "difficulty": 1,
            "latex_expression": expression,
            "parameters": parameters,
            "total_steps": len(steps),
            "steps": steps
        })

    except mysql.connector.Error:
        app.logger.exception("產生題目與解題步驟失敗")

        return jsonify({
            "error": "資料庫查詢失敗"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# ==========================================
# 12. 啟動 Flask
# ==========================================

if __name__ == "__main__":
    print("===== Flask 路由清單 =====")
    print(app.url_map)

    app.run(debug=True)
