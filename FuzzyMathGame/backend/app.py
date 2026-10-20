
from flask import Flask, jsonify, send_from_directory, request
from calculation_engine import calculate_answer
from fuzzy_difficulty import select_difficulty
from fuzzy_ability import calculate_ability_change

import mysql.connector
import os
import json
import random
import math
import re


# ============================================================
# 1. Flask 基本設定
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

app = Flask(
    __name__,
    static_folder=BASE_DIR,
    static_url_path="/static"
)

app.json.ensure_ascii = False


def data_mode():
    config = os.path.join(BASE_DIR, "database", "runtime.json")
    if os.path.exists(config):
        with open(config, encoding="utf-8") as source:
            return json.load(source)["mode"]
    return os.getenv("FUZZY_DATA_MODE", "local")


@app.get("/api/game-config")
def game_config():
    mode = data_mode()
    try:
        if mode == "mysql_dev":
            from dev_bank import catalog
            chapters = catalog()
            return jsonify(mode=mode, label="MySQL 開發題庫（自編代表題）", chapters=chapters,
                           type_ids=chapters.get("1", []))
        local = mode == "local"
        ids = ["F01", "F02", "F03", "F04"] if local else [f"F{i:02}" for i in range(1, 21)]
        return jsonify(mode=mode, label="本機練習題庫" if local else "原始 MySQL 題庫",
                       type_ids=ids, chapters={"1": ids})
    except Exception:
        app.logger.exception("題庫設定讀取失敗")
        return jsonify(status="error", message="題庫連線失敗，請檢查本機資料庫和密碼設定。"), 503


# ============================================================
# 2. MySQL 資料庫連線
# ============================================================

def get_db_connection():
    password = os.getenv("FUZZY_DB_PASSWORD")

    if password is None:
        raise RuntimeError(
            "尚未設定環境變數 FUZZY_DB_PASSWORD，"
            "請先設定 MySQL 資料庫密碼。"
        )

    return mysql.connector.connect(
        host=os.getenv("FUZZY_DB_HOST", "localhost"),
        port=int(os.getenv("FUZZY_DB_PORT", "3306")),
        user=os.getenv("FUZZY_DB_USER", "root"),
        password=password,
        database=os.getenv(
            "FUZZY_DB_NAME",
            "fuzzy_math_game"
        )
    )


# ============================================================
# 3. 共用資料處理工具
# ============================================================

def parse_json_value(value, default=None):
    if value is None:
        return default

    if isinstance(value, (dict, list, int, float, bool)):
        return value

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return default

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default

    return default


def format_parameter(value):
    if isinstance(value, bool):
        return str(value)

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(
                "參數不能是無限大或 NaN。"
            )

        if value.is_integer():
            return str(int(value))

        return str(value)

    return str(value)


def normalize_number(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value

    if isinstance(value, str):
        value = value.strip()

        try:
            number = float(value)

            if not math.isfinite(number):
                return value

            if number.is_integer():
                return int(number)

            return number

        except ValueError:
            return value

    return value


def is_numeric(value):
    if isinstance(value, bool):
        return False

    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def normalize_answer_text(value):
    text = str(value).strip()

    text = text.replace("−", "-")
    text = text.replace("＋", "+")
    text = text.replace("＝", "=")
    text = text.replace("＊", "*")
    text = text.replace("／", "/")

    text = re.sub(r"\s+", "", text)
    text = text.replace("\u3000", "")

    return text


def compare_answers(correct_answer, user_answer):
    if correct_answer is None or user_answer is None:
        return False

    correct = normalize_number(correct_answer)
    submitted = normalize_number(user_answer)

    if (
        not isinstance(correct, bool)
        and not isinstance(submitted, bool)
        and isinstance(correct, (int, float))
        and isinstance(submitted, (int, float))
    ):
        return math.isclose(
            float(correct),
            float(submitted),
            rel_tol=1e-9,
            abs_tol=1e-9
        )

    return (
        normalize_answer_text(correct)
        ==
        normalize_answer_text(submitted)
    )


# ============================================================
# 4. 數學格式整理與模板替換
# ============================================================

def clean_expression(expression):
    if expression is None:
        return None

    text = str(expression)

    text = text.replace("+-", "-")
    text = text.replace("--", "+")

    text = re.sub(
        r"(?<![A-Za-z0-9_.])-?1x\b",
        lambda match: (
            "-x"
            if match.group(0).startswith("-")
            else "x"
        ),
        text
    )

    return text


def render_template(template, parameters):
    """
    嚴格替換 {{parameter}}。
    缺少必要參數時直接報錯。
    """

    if template is None:
        return None

    text = str(template)

    def replace_parameter(match):
        name = match.group(1).strip()

        if name not in parameters:
            raise ValueError(
                f"模板需要參數 {name}，"
                "但目前沒有提供此參數。"
            )

        return format_parameter(parameters[name])

    text = re.sub(
        r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}",
        replace_parameter,
        text
    )

    return clean_expression(text)


def render_template_loose(template, parameters):
    """
    替換已知參數。
    未知參數及 {{blank:key}} 標記保留。
    """

    if template is None:
        return None

    text = str(template)

    def replace_parameter(match):
        name = match.group(1).strip()

        if name not in parameters:
            return match.group(0)

        return format_parameter(parameters[name])

    text = re.sub(
        r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}",
        replace_parameter,
        text
    )

    return clean_expression(text)


# ============================================================
# 5. 動態挖空標記處理
# ============================================================

def extract_blank_keys(template):
    if template is None:
        return []

    return re.findall(
        r"\{\{\s*blank:([A-Za-z_][A-Za-z0-9_]*)\s*\}\}",
        str(template)
    )


def prepare_template_parameters(
    spec_id,
    parameters,
    answer
):
    template_parameters = dict(parameters)
    template_parameters["answer"] = answer

    if (
        spec_id.startswith("F01_")
        and "a" in parameters
        and "v" in parameters
    ):
        product = (
            float(parameters["a"])
            * float(parameters["v"])
        )

        template_parameters["product"] = normalize_number(
            product
        )

    return template_parameters


# ============================================================
# 6. allow_zero 與參數生成
# ============================================================

def parse_allow_zero(value):
    if isinstance(value, str):
        return value.strip().lower() not in (
            "0", "false", "no", "n"
        )

    return bool(value)


def generate_parameter_value(rule):
    data_type = str(
        rule.get("data_type") or "INTEGER"
    ).upper()

    minimum = rule.get("min_value")
    maximum = rule.get("max_value")

    if minimum is None:
        minimum = rule.get("default_min")

    if maximum is None:
        maximum = rule.get("default_max")

    if minimum is None:
        minimum = -5

    if maximum is None:
        maximum = 5

    minimum = float(minimum)
    maximum = float(maximum)

    if (
        not math.isfinite(minimum)
        or not math.isfinite(maximum)
    ):
        raise ValueError(
            "參數範圍不能包含無限大或 NaN。"
        )

    if minimum > maximum:
        raise ValueError(
            f"參數範圍錯誤：最小值 {minimum} "
            f"大於最大值 {maximum}。"
        )

    excluded_values = parse_json_value(
        rule.get("excluded_values"),
        []
    )

    if not isinstance(excluded_values, list):
        excluded_values = []

    excluded_numbers = {
        float(value)
        for value in excluded_values
        if is_numeric(value)
    }

    allow_zero = parse_allow_zero(
        rule.get("allow_zero", True)
    )

    if data_type in (
        "INTEGER",
        "POSITIVE_INTEGER",
        "NONZERO_INTEGER"
    ):
        low = math.ceil(minimum)
        high = math.floor(maximum)

        if data_type == "POSITIVE_INTEGER":
            low = max(low, 1)

        candidates = list(range(low, high + 1))

        if data_type == "NONZERO_INTEGER":
            candidates = [
                value for value in candidates
                if value != 0
            ]

        if not allow_zero:
            candidates = [
                value for value in candidates
                if value != 0
            ]

        candidates = [
            value for value in candidates
            if float(value) not in excluded_numbers
        ]

        if not candidates:
            raise ValueError(
                "參數範圍、資料型態、排除值或 allow_zero "
                "限制互相衝突，沒有可用的參數。"
            )

        return random.choice(candidates)

    if data_type == "DECIMAL":
        low_tenths = math.ceil(minimum * 10)
        high_tenths = math.floor(maximum * 10)

        candidates = []

        for value in range(low_tenths, high_tenths + 1):
            number = value / 10

            if not allow_zero and number == 0:
                continue

            if number in excluded_numbers:
                continue

            candidates.append(number)

        if not candidates:
            raise ValueError(
                "DECIMAL 參數範圍內沒有可用的數值。"
            )

        return random.choice(candidates)

    raise ValueError(
        f"目前不支援參數資料型態：{data_type}"
    )


# ============================================================
# 7. 取得題目規格並生成題目
# ============================================================

def build_question(cursor, type_id, difficulty):
    cursor.execute(
        """
        SELECT
            spec_id,
            type_id,
            difficulty,
            question_template,
            question_latex_template,
            answer_rule
        FROM question_spec
        WHERE type_id = %s
          AND difficulty = %s
        LIMIT 1
        """,
        (type_id, difficulty)
    )

    spec = cursor.fetchone()

    if not spec:
        raise LookupError(
            f"找不到題型 {type_id} 的難度 {difficulty} 規格。"
        )

    cursor.execute(
        """
        SELECT
            sp.parameter_name,
            sp.parameter_code,
            sp.min_value,
            sp.max_value,
            sp.excluded_values,
            sp.constraint_rule,
            pd.data_type,
            pd.default_min,
            pd.default_max,
            pd.allow_zero
        FROM spec_parameter AS sp
        JOIN parameter_definition AS pd
          ON sp.parameter_code = pd.parameter_code
        WHERE sp.spec_id = %s
        ORDER BY sp.parameter_name
        """,
        (spec["spec_id"],)
    )

    parameter_rules = cursor.fetchall()

    parameters = {}

    for rule in parameter_rules:
        name = rule["parameter_name"]

        if name in parameters:
            raise ValueError(
                f"題目 {spec['spec_id']} 出現重複參數名稱：{name}"
            )

        parameters[name] = generate_parameter_value(rule)

    question_text = render_template(
        spec.get("question_template"),
        parameters
    )

    question_latex = render_template(
        spec.get("question_latex_template"),
        parameters
    )

    return {
        "spec": spec,
        "parameters": parameters,
        "question_text": question_text,
        "question_latex": question_latex
    }


# ============================================================
# 8. 驗證玩家提交的參數
# ============================================================

def validate_submitted_parameters(
    cursor,
    spec_id,
    submitted_parameters
):
    if not isinstance(submitted_parameters, dict):
        return False, "parameters 必須是 JSON 物件。"

    cursor.execute(
        """
        SELECT
            sp.parameter_name,
            sp.parameter_code,
            sp.min_value,
            sp.max_value,
            sp.excluded_values,
            sp.constraint_rule,
            pd.data_type,
            pd.default_min,
            pd.default_max,
            pd.allow_zero
        FROM spec_parameter AS sp
        JOIN parameter_definition AS pd
          ON sp.parameter_code = pd.parameter_code
        WHERE sp.spec_id = %s
        """,
        (spec_id,)
    )

    rules = cursor.fetchall()

    allowed_names = {
        rule["parameter_name"] for rule in rules
    }

    submitted_names = set(submitted_parameters.keys())

    if submitted_names != allowed_names:
        missing = sorted(allowed_names - submitted_names)
        extra = sorted(submitted_names - allowed_names)

        messages = []

        if missing:
            messages.append(
                "缺少參數：" + ", ".join(missing)
            )

        if extra:
            messages.append(
                "多餘參數：" + ", ".join(extra)
            )

        return False, "；".join(messages)

    for rule in rules:
        name = rule["parameter_name"]
        value = submitted_parameters[name]

        if not is_numeric(value):
            return False, f"參數 {name} 必須是有效數值。"

        number = float(value)

        minimum = rule.get("min_value")
        maximum = rule.get("max_value")

        if minimum is None:
            minimum = rule.get("default_min")

        if maximum is None:
            maximum = rule.get("default_max")

        if minimum is not None and number < float(minimum):
            return False, f"參數 {name} 小於允許的最小值。"

        if maximum is not None and number > float(maximum):
            return False, f"參數 {name} 大於允許的最大值。"

        data_type = str(
            rule.get("data_type") or "INTEGER"
        ).upper()

        if data_type in (
            "INTEGER",
            "POSITIVE_INTEGER",
            "NONZERO_INTEGER"
        ):
            if not number.is_integer():
                return False, f"參數 {name} 必須是整數。"

        if data_type == "POSITIVE_INTEGER" and number <= 0:
            return False, f"參數 {name} 必須是正整數。"

        if data_type == "NONZERO_INTEGER" and number == 0:
            return False, f"參數 {name} 不能是 0。"

        excluded_values = parse_json_value(
            rule.get("excluded_values"),
            []
        )

        if not isinstance(excluded_values, list):
            excluded_values = []

        for excluded in excluded_values:
            if is_numeric(excluded) and math.isclose(
                number,
                float(excluded),
                rel_tol=1e-9,
                abs_tol=1e-9
            ):
                return False, f"參數 {name} 使用了不允許的數值。"

        allow_zero = parse_allow_zero(
            rule.get("allow_zero", True)
        )

        if not allow_zero and number == 0:
            return False, f"參數 {name} 不允許為 0。"

    return True, "參數驗證成功。"


# ============================================================
# 9. 取得解題步驟與填空
# ============================================================

def get_steps_and_blanks(
    cursor,
    spec_id,
    parameters,
    answer
):
    template_parameters = prepare_template_parameters(
        spec_id,
        parameters,
        answer
    )

    cursor.execute(
        """
        SELECT *
        FROM solution_step
        WHERE spec_id = %s
        ORDER BY step_order, step_id
        """,
        (spec_id,)
    )

    steps = []

    for row in cursor.fetchall():
        step = dict(row)

        original_latex = step.get("step_latex_template")

        step["blank_keys"] = extract_blank_keys(
            original_latex
        )

        for key in (
            "step_template",
            "step_latex_template",
            "step_description",
            "hint",
            "answer_template"
        ):
            if key in step and step[key] is not None:
                step[key] = render_template_loose(
                    step[key],
                    template_parameters
                )

        steps.append(step)

    cursor.execute(
        """
        SELECT *
        FROM blank_rule
        WHERE spec_id = %s
        ORDER BY step_order, blank_level, blank_id
        """,
        (spec_id,)
    )

    blanks = []

    for row in cursor.fetchall():
        blank = dict(row)

        for key in (
            "correct_answer_template",
            "target_expression",
            "hint"
        ):
            if key in blank and blank[key] is not None:
                blank[key] = render_template_loose(
                    blank[key],
                    template_parameters
                )

        blanks.append(blank)

    return steps, blanks


# ============================================================
# 10. 統一錯誤回應
# ============================================================

def error_response(message, status_code=400):
    return jsonify({
        "status": "error",
        "message": str(message)
    }), status_code


# ============================================================
# 11. 首頁
# ============================================================

@app.route("/")
def home():
    if not os.path.isfile(
        os.path.join(BASE_DIR, "index.html")
    ):
        return error_response(
            "找不到 index.html，請確認前端檔案位置。",
            404
        )

    return send_from_directory(BASE_DIR, "index.html")


# ============================================================
# 12. API 測試
# ============================================================

@app.route("/api/test", methods=["GET"])
def api_test():
    return jsonify({
        "status": "success",
        "message": "Flask API 運作正常。",
        "project": "Fuzzy Math Game",
        "base_dir": BASE_DIR
    })


# ============================================================
# 13. 資料庫狀態檢查
# ============================================================

@app.route("/api/db-check", methods=["GET"])
def db_check():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        table_names = [
            "question_type",
            "question_spec",
            "parameter_definition",
            "spec_parameter",
            "generation_rule",
            "solution_step",
            "blank_rule"
        ]

        counts = {}

        for table_name in table_names:
            cursor.execute(
                f"SELECT COUNT(*) AS total FROM `{table_name}`"
            )

            counts[table_name] = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT
                spec_id,
                type_id,
                difficulty,
                answer_rule
            FROM question_spec
            ORDER BY type_id, difficulty
            LIMIT 5
            """
        )

        first_specs = cursor.fetchall()

        return jsonify({
            "status": "success",
            "message": "資料庫連線成功。",
            "table_counts": counts,
            "first_specs": first_specs
        })

    except Exception as exc:
        app.logger.exception("資料庫狀態檢查失敗")
        return error_response(
            f"資料庫檢查失敗：{exc}",
            500
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# 14. 取得題型清單
# ============================================================

@app.route("/api/question-types", methods=["GET"])
def get_question_types():
    connection = None
    cursor = None

    try:
        chapter = request.args.get("chapter", type=int)

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SHOW COLUMNS FROM question_type")
        columns = cursor.fetchall()

        column_names = {
            column["Field"] for column in columns
        }

        if "chapter" in column_names:
            order_by = "`chapter`"
        else:
            order_by = None

        if "type_id" in column_names:
            order_by = (
                f"{order_by}, `type_id`"
                if order_by else "`type_id`"
            )
        elif "question_type_id" in column_names:
            order_by = (
                f"{order_by}, `question_type_id`"
                if order_by else "`question_type_id`"
            )

        sql = "SELECT * FROM question_type"
        values = []

        if chapter is not None:
            if "chapter" not in column_names:
                return error_response(
                    "question_type 資料表沒有 chapter 欄位。",
                    500
                )

            sql += " WHERE chapter = %s"
            values.append(chapter)

        if order_by:
            sql += f" ORDER BY {order_by}"

        cursor.execute(sql, tuple(values))
        rows = cursor.fetchall()

        return jsonify({
            "status": "success",
            "total": len(rows),
            "question_types": rows
        })

    except Exception as exc:
        app.logger.exception("取得題型清單失敗")
        return error_response(
            f"取得題型清單失敗：{exc}",
            500
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# 15. 取得題目規格
# ============================================================

@app.route("/api/question-specs", methods=["GET"])
def get_question_specs():
    connection = None
    cursor = None

    try:
        type_id = request.args.get("type_id")
        difficulty = request.args.get(
            "difficulty",
            type=int
        )

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT *
            FROM question_spec
            WHERE 1 = 1
        """

        values = []

        if type_id:
            sql += " AND type_id = %s"
            values.append(type_id)

        if difficulty is not None:
            sql += " AND difficulty = %s"
            values.append(difficulty)

        sql += " ORDER BY type_id, difficulty"

        cursor.execute(sql, tuple(values))
        specs = cursor.fetchall()

        for spec in specs:
            spec["example_parameters"] = parse_json_value(
                spec.get("example_parameters"),
                {}
            )

        return jsonify({
            "status": "success",
            "total": len(specs),
            "question_specs": specs
        })

    except Exception as exc:
        app.logger.exception("取得題目規格失敗")
        return error_response(
            f"取得題目規格失敗：{exc}",
            500
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# 16. 生成題目
# ============================================================

@app.route(
    "/api/questions/generate/<type_id>",
    methods=["GET"]
)
def generate_question(type_id):
    connection = None
    cursor = None

    try:
        difficulty = request.args.get(
            "difficulty",
            default=1,
            type=int
        )

        if difficulty not in (1, 2, 3, 4, 5):
            return error_response(
                "difficulty 必須介於 1 到 5。",
                400
            )

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        question = build_question(
            cursor,
            type_id,
            difficulty
        )

        spec = question["spec"]
        parameters = question["parameters"]

        answer = calculate_answer(
            type_id,
            difficulty,
            parameters,
            spec["answer_rule"]
        )

        return jsonify({
            "status": "success",
            "message": "題目生成成功。",
            "spec_id": spec["spec_id"],
            "type_id": type_id,
            "difficulty": difficulty,
            "question_text": question["question_text"],
            "question_latex": question["question_latex"],
            "parameters": parameters,
            "answer_rule": spec["answer_rule"],
            "answer": answer
        })

    except LookupError as exc:
        return error_response(str(exc), 404)

    except Exception as exc:
        app.logger.exception("生成題目失敗")
        return error_response(
            f"生成題目失敗：{exc}",
            500
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# 17. 生成題目、標準解題步驟與填空
# ============================================================

@app.route(
    "/api/questions/generate-with-steps/<type_id>",
    methods=["GET"]
)
def generate_question_with_steps(type_id):
    connection = None
    cursor = None

    try:
        ability_text = request.args.get("ability")
        adaptive_result = None

        if ability_text is not None:
            try:
                ability = float(ability_text)
            except (TypeError, ValueError):
                return error_response(
                    "ability 必須是 0 到 100 之間的數值。",
                    400
                )

            if not math.isfinite(ability) or not 0 <= ability <= 100:
                return error_response(
                    "ability 必須介於 0 到 100。",
                    400
                )

            adaptive_result = select_difficulty(ability)
            difficulty = int(adaptive_result["difficulty"])

        else:
            difficulty = request.args.get(
                "difficulty",
                default=1,
                type=int
            )

        if difficulty not in (1, 2, 3, 4, 5):
            return error_response(
                "difficulty 必須介於 1 到 5。",
                400
            )

        if data_mode() == "local":
            from local_questions import generate
            return jsonify(generate(type_id, difficulty))

        if data_mode() == "mysql_dev":
            from dev_bank import generate
            return jsonify(generate(type_id, difficulty))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        question = build_question(
            cursor,
            type_id,
            difficulty
        )

        spec = question["spec"]
        parameters = question["parameters"]

        answer = calculate_answer(
            type_id,
            difficulty,
            parameters,
            spec["answer_rule"]
        )

        steps, blanks = get_steps_and_blanks(
            cursor,
            spec["spec_id"],
            parameters,
            answer
        )

        response_data = {
            "status": "success",
            "message": "題目與解題資料取得成功。",
            "spec_id": spec["spec_id"],
            "type_id": type_id,
            "difficulty": difficulty,
            "question_text": question["question_text"],
            "question_latex": question["question_latex"],
            "parameters": parameters,
            "answer_rule": spec["answer_rule"],
            "answer": answer,
            "steps": steps,
            "blanks": blanks,
            "total_steps": len(steps),
            "total_blanks": len(blanks),
            "adaptive": adaptive_result is not None
        }

        if adaptive_result is not None:
            response_data["ability"] = adaptive_result.get(
                "ability",
                ability
            )

            response_data["difficulty_memberships"] = (
                adaptive_result.get("memberships", {})
            )

            response_data["difficulty_probabilities"] = (
                adaptive_result.get("probabilities", {})
            )

        return jsonify(response_data)

    except LookupError as exc:
        return error_response(str(exc), 404)

    except Exception as exc:
        app.logger.exception(
            "生成題目及解題步驟失敗"
        )

        return error_response(
            f"生成題目及解題步驟失敗：{exc}",
            500
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# 18. 玩家答案驗證
# ============================================================

@app.route("/api/answers/check", methods=["POST"])
def check_answer():
    connection = None
    cursor = None

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return error_response(
                "請提交有效的 JSON 物件。",
                400
            )

        spec_id = data.get("spec_id")
        type_id = data.get("type_id")
        difficulty = data.get("difficulty")
        parameters = data.get("parameters")
        user_answer = data.get("user_answer")

        if not spec_id or not type_id:
            return error_response(
                "缺少 spec_id 或 type_id。",
                400
            )

        if difficulty is None:
            return error_response(
                "缺少 difficulty。",
                400
            )

        try:
            difficulty = int(difficulty)
        except (TypeError, ValueError):
            return error_response(
                "difficulty 必須是整數。",
                400
            )

        if difficulty not in (1, 2, 3, 4, 5):
            return error_response(
                "difficulty 必須介於 1 到 5。",
                400
            )

        if user_answer is None:
            return error_response(
                "缺少 user_answer。",
                400
            )

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM question_spec
            WHERE spec_id = %s
              AND type_id = %s
              AND difficulty = %s
            LIMIT 1
            """,
            (spec_id, type_id, difficulty)
        )

        spec = cursor.fetchone()

        if not spec:
            return error_response(
                "找不到符合條件的題目規格。",
                404
            )

        valid, message = validate_submitted_parameters(
            cursor,
            spec_id,
            parameters
        )

        if not valid:
            return error_response(message, 400)

        correct_answer = calculate_answer(
            type_id,
            difficulty,
            parameters,
            spec["answer_rule"]
        )

        is_correct = compare_answers(
            correct_answer,
            user_answer
        )

        return jsonify({
            "status": "success",
            "spec_id": spec_id,
            "type_id": type_id,
            "difficulty": difficulty,
            "is_correct": is_correct,
            "message": (
                "回答正確！"
                if is_correct
                else "答案不正確，請再檢查計算過程。"
            )
        })

    except Exception as exc:
        app.logger.exception("答案驗證失敗")
        return error_response(
            f"答案驗證失敗：{exc}",
            500
        )

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# 19. Fuzzy 能力值增減 API（本次新增）
# ============================================================

@app.route("/api/ability/change", methods=["POST"])
def api_ability_change():
    """
    接收前端提供的遊戲狀態，
    呼叫 fuzzy_ability.py 計算能力值增減。

    POST JSON 範例：
    {
        "remaining_hp": 75,
        "hint_count": 1,
        "difficulty": 3,
        "elapsed_time": 45,
        "is_correct": true,
        "current_ability": 50
    }
    """

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return error_response(
                "請提交有效的 JSON 物件。",
                400
            )

        required_fields = [
            "remaining_hp",
            "hint_count",
            "difficulty",
            "elapsed_time",
            "is_correct",
            "current_ability"
        ]

        missing_fields = [
            field
            for field in required_fields
            if field not in data
        ]

        if missing_fields:
            return error_response(
                "缺少必要欄位："
                + ", ".join(missing_fields),
                400
            )

        # ----------------------------------------------------
        # 1. 驗證數值欄位
        # ----------------------------------------------------

        numeric_fields = [
            "remaining_hp",
            "difficulty",
            "elapsed_time",
            "current_ability"
        ]

        for field in numeric_fields:
            value = data[field]

            if isinstance(value, bool) or not isinstance(
                value, (int, float)
            ):
                return error_response(
                    f"{field} 必須是數值。",
                    400
                )

            if not math.isfinite(value):
                return error_response(
                    f"{field} 必須是有限數值。",
                    400
                )

        remaining_hp = data["remaining_hp"]
        difficulty_value = data["difficulty"]
        elapsed_time = data["elapsed_time"]
        current_ability = data["current_ability"]

        # ----------------------------------------------------
        # 2. 驗證 HP
        # ----------------------------------------------------

        if not 0 <= remaining_hp <= 100:
            return error_response(
                "remaining_hp 必須介於 0 到 100。",
                400
            )

        # fuzzy_ability.py 目前要求 HP 為指定離散值。
        if remaining_hp not in (0, 25, 50, 75, 100):
            return error_response(
                "remaining_hp 必須為 0、25、50、75 或 100。",
                400
            )

        # ----------------------------------------------------
        # 3. 驗證提示次數
        # ----------------------------------------------------

        hint_count = data["hint_count"]

        if (
            not isinstance(hint_count, int)
            or isinstance(hint_count, bool)
        ):
            return error_response(
                "hint_count 必須是整數。",
                400
            )

        if not 0 <= hint_count <= 5:
            return error_response(
                "hint_count 必須介於 0 到 5。",
                400
            )

        # ----------------------------------------------------
        # 4. 驗證難度
        # ----------------------------------------------------

        if (
            not isinstance(difficulty_value, int)
            or isinstance(difficulty_value, bool)
            or difficulty_value not in (1, 2, 3, 4, 5)
        ):
            return error_response(
                "difficulty 必須是 1 到 5 的整數。",
                400
            )

        difficulty = difficulty_value

        # ----------------------------------------------------
        # 5. 驗證作答時間
        # ----------------------------------------------------

        if elapsed_time < 0:
            return error_response(
                "elapsed_time 不可小於 0。",
                400
            )

        # ----------------------------------------------------
        # 6. 驗證答題結果
        # ----------------------------------------------------

        is_correct = data["is_correct"]

        if not isinstance(is_correct, bool):
            return error_response(
                "is_correct 必須是 true 或 false。",
                400
            )

        # ----------------------------------------------------
        # 7. 驗證目前能力值
        # ----------------------------------------------------

        if not 0 <= current_ability <= 100:
            return error_response(
                "current_ability 必須介於 0 到 100。",
                400
            )

        # ----------------------------------------------------
        # 8. 呼叫 Fuzzy 能力值計算
        # ----------------------------------------------------

        result = calculate_ability_change(
            remaining_hp=remaining_hp,
            hint_count=hint_count,
            difficulty=difficulty,
            elapsed_time=elapsed_time,
            is_correct=is_correct,
            current_ability=current_ability
        )

        # ----------------------------------------------------
        # 9. 回傳實際計算結果
        # ----------------------------------------------------

        return jsonify({
            "status": "success",
            "message": "Fuzzy 能力值計算完成。",
            "ability_change": result["ability_change"],
            "new_ability": result["new_ability"],
            "details": result["details"]
        })

    except (TypeError, ValueError) as exc:
        return error_response(
            f"能力值計算輸入錯誤：{exc}",
            400
        )

    except Exception as exc:
        app.logger.exception(
            "Fuzzy 能力值計算失敗"
        )

        return error_response(
            f"Fuzzy 能力值計算失敗：{exc}",
            500
        )


# ============================================================
# 20. 舊版 API 相容處理
# ============================================================

@app.route("/api/questions", methods=["GET"])
def legacy_questions():
    return error_response(
        "此 API 已停用，請改用 "
        "/api/questions/generate/<type_id>。",
        410
    )


@app.route("/api/questions/<type_id>", methods=["GET"])
def legacy_question_by_type(type_id):
    return error_response(
        "此 API 已停用，請改用 "
        f"/api/questions/generate/{type_id}。",
        410
    )


@app.route("/api/parameters/<type_id>", methods=["GET"])
def legacy_parameters(type_id):
    return error_response(
        "此 API 已停用，參數現在由題目生成 API 一併提供。",
        410
    )


@app.route(
    "/api/solution-steps/<type_id>/<int:difficulty>",
    methods=["GET"]
)
def legacy_solution_steps(type_id, difficulty):
    return error_response(
        "此 API 已停用，請改用 "
        f"/api/questions/generate-with-steps/{type_id}"
        f"?difficulty={difficulty}。",
        410
    )


# ============================================================
# 21. 列出目前 API 路由
# ============================================================

@app.route("/api/routes", methods=["GET"])
def list_routes():
    routes = []

    for rule in app.url_map.iter_rules():
        routes.append({
            "endpoint": rule.endpoint,
            "methods": sorted(
                method for method in rule.methods
                if method not in ("HEAD", "OPTIONS")
            ),
            "path": str(rule)
        })

    routes.sort(key=lambda item: item["path"])

    return jsonify({
        "status": "success",
        "total": len(routes),
        "routes": routes
    })


# ============================================================
# 22. 啟動 Flask
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Fuzzy Math Game Backend")
    print("BASE_DIR =", BASE_DIR)
    print(
        "index.html exists =",
        os.path.exists(os.path.join(BASE_DIR, "index.html"))
    )
    print(
        "CSS exists =",
        os.path.exists(os.path.join(BASE_DIR, "css", "style.css"))
    )
    print(
        "JS exists =",
        os.path.exists(os.path.join(BASE_DIR, "js", "main.js"))
    )
    print("=" * 60)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
