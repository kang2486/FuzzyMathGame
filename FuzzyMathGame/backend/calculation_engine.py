
"""
calculation_engine.py

FuzzyMathGame 數學答案計算引擎
支援 F01～F20，難度 1～5。

本模組不連接 MySQL，也不建立 Flask。
由 app.py 傳入：
    type_id
    difficulty
    parameters
    answer_rule

所有答案以字串回傳，方便前端顯示公式、區間與文字答案。
"""

from fractions import Fraction
from math import isqrt


# ============================================================
# 1. 共用工具
# ============================================================

def number(value):
    """將整數、小數或分數轉成精確 Fraction。"""
    if isinstance(value, Fraction):
        return value

    if isinstance(value, bool):
        raise ValueError("布林值不能作為數學參數")

    return Fraction(str(value).strip())


def param(parameters, name):
    """取得必要參數。"""
    if name not in parameters:
        raise ValueError(f"缺少必要參數：{name}")

    return number(parameters[name])


def fmt(value):
    """整數輸出整數，分數輸出 n/d。"""
    value = number(value)

    if value.denominator == 1:
        return str(value.numerator)

    return f"{value.numerator}/{value.denominator}"


def signed_term(value, variable=""):
    """格式化帶正負號的項，例如 +3x、-2、+x。"""
    value = number(value)

    if value == 0:
        return ""

    sign = "+" if value > 0 else "-"
    absolute = abs(value)

    if variable and absolute == 1:
        coefficient = ""
    else:
        coefficient = fmt(absolute)

    return f"{sign}{coefficient}{variable}"


def polynomial_to_string(terms, variable="x"):
    """
    將多項式轉成字串。
    terms 格式：{次方: 係數}
    例如 {2: 2, 1: -3, 0: 1} -> 2x^2 - 3x + 1
    """
    clean = {}

    for power, coefficient in terms.items():
        power = int(power)
        coefficient = number(coefficient)

        if coefficient != 0:
            clean[power] = coefficient

    if not clean:
        return "0"

    result = []

    for power in sorted(clean, reverse=True):
        coefficient = clean[power]
        negative = coefficient < 0
        absolute = abs(coefficient)

        if power == 0:
            body = fmt(absolute)
        else:
            coefficient_text = (
                "" if absolute == 1 else fmt(absolute)
            )

            if power == 1:
                body = f"{coefficient_text}{variable}"
            else:
                body = f"{coefficient_text}{variable}^{power}"

        if not result:
            result.append(
                ("-" if negative else "") + body
            )
        else:
            result.append(
                (" - " if negative else " + ") + body
            )

    return "".join(result)


def polynomial_add(*polynomials):
    result = {}

    for polynomial in polynomials:
        for power, coefficient in polynomial.items():
            result[power] = (
                result.get(power, Fraction(0))
                + number(coefficient)
            )

    return {
        power: coefficient
        for power, coefficient in result.items()
        if coefficient != 0
    }


def polynomial_multiply(poly1, poly2):
    result = {}

    for power1, coefficient1 in poly1.items():
        for power2, coefficient2 in poly2.items():
            power = power1 + power2

            result[power] = (
                result.get(power, Fraction(0))
                + number(coefficient1) * number(coefficient2)
            )

    return {
        power: coefficient
        for power, coefficient in result.items()
        if coefficient != 0
    }


def polynomial_power(polynomial, exponent):
    exponent = int(exponent)

    if exponent < 0:
        raise ValueError("多項式次方不能為負數")

    result = {0: Fraction(1)}
    base = dict(polynomial)

    while exponent:
        if exponent % 2:
            result = polynomial_multiply(result, base)

        base = polynomial_multiply(base, base)
        exponent //= 2

    return result


def equation_x(value):
    return f"x={fmt(value)}"


def two_roots(root1, root2):
    return f"x={fmt(root1)} 或 x={fmt(root2)}"


def reverse_inequality(operator):
    operators = {
        ">": "<",
        "<": ">",
        ">=": "<=",
        "<=": ">="
    }

    if operator not in operators:
        raise ValueError(f"不支援的不等式符號：{operator}")

    return operators[operator]


def solve_inequality(A, B, operator, C):
    """解 A*x+B operator C。"""
    A, B, C = number(A), number(B), number(C)

    if A == 0:
        raise ValueError("不等式的 x 係數不能為 0")

    answer = (C - B) / A

    if A < 0:
        operator = reverse_inequality(operator)

    return f"x{operator}{fmt(answer)}"


def sqrt_fraction(value):
    """若有理數的平方根仍是有理數，回傳其平方根；否則回傳 None。"""
    value = number(value)

    if value < 0:
        return None

    n = isqrt(value.numerator)
    d = isqrt(value.denominator)

    if (
        n * n == value.numerator
        and d * d == value.denominator
    ):
        return Fraction(n, d)

    return None



def quadratic_roots(a, b, c):
    """
    求解 ax²+bx+c=0。

    回傳規則：
    1. 判別式小於 0：回傳 None，代表沒有實數解。
    2. 判別式的平方根是有理數：回傳有理數根。
    3. 判別式的平方根不是有理數：回傳根號形式所需的資料。
    """
    a, b, c = number(a), number(b), number(c)

    if a == 0:
        raise ValueError("二次項係數不能為 0")

    discriminant = b * b - 4 * a * c

    # 判別式小於 0，沒有實數解
    if discriminant < 0:
        return None

    # 嘗試取得有理數平方根
    root_d = sqrt_fraction(discriminant)

    if root_d is not None:
        root1 = (-b + root_d) / (2 * a)
        root2 = (-b - root_d) / (2 * a)

        return ("rational", root1, root2)

    # 無理數根：保留公式中的 -b、判別式及 2a
    return (
        "irrational",
        -b,
        discriminant,
        2 * a
    )


# ============================================================
# 2. F01：函數值計算
# ============================================================

def answer_f01(rule, difficulty, p):
    v = param(p, "v")

    if rule == "FUNCTION_VALUE_LINEAR":
        result = param(p, "a") * v + param(p, "b")

    elif rule == "FUNCTION_VALUE_QUADRATIC":
        result = (
            param(p, "a") * v**2
            + param(p, "b") * v
            + param(p, "c")
        )

    elif rule == "FUNCTION_VALUE_CUBIC":
        result = (
            v**3
            + param(p, "a") * v**2
            + param(p, "b") * v
            + param(p, "c")
        )

    elif rule == "FUNCTION_VALUE_QUARTIC":
        result = (
            v**4
            + param(p, "a") * v**3
            + param(p, "b") * v**2
            + param(p, "c") * v
            + param(p, "d")
        )

    else:
        raise ValueError(f"F01 未知規則：{rule}")

    return fmt(result)


# ============================================================
# 3. F02：多項式同類項合併
# ============================================================

def answer_f02(rule, difficulty, p):
    a, b = param(p, "a"), param(p, "b")

    if rule == "POLY_COMBINE_LINEAR":
        terms = {1: a + b}

    elif rule == "POLY_COMBINE_LINEAR_CONSTANT":
        terms = {1: a - b, 0: param(p, "c")}

    elif rule == "POLY_COMBINE_QUADRATIC":
        terms = {
            2: a + param(p, "c"),
            1: b + param(p, "d")
        }

    elif rule == "POLY_COMBINE_QUADRATIC_CONSTANT":
        terms = {
            2: a + param(p, "d"),
            1: b + param(p, "e"),
            0: param(p, "c") + param(p, "f")
        }

    elif rule == "POLY_COMBINE_CUBIC":
        terms = {
            3: a + param(p, "e"),
            2: b + param(p, "f"),
            1: param(p, "c") + param(p, "g"),
            0: param(p, "d") + param(p, "h")
        }

    else:
        raise ValueError(f"F02 未知規則：{rule}")

    return polynomial_to_string(terms)


# ============================================================
# 4. F03：括號與分配律
# ============================================================

def answer_f03(rule, difficulty, p):
    a, b = param(p, "a"), param(p, "b")

    if rule == "DISTRIBUTE_LINEAR":
        terms = {
            1: a * b,
            0: a * param(p, "c")
        }

    elif rule == "DISTRIBUTE_AND_COMBINE":
        terms = {
            1: a * b,
            0: -a * param(p, "c") + param(p, "d")
        }

    elif rule == "DISTRIBUTE_SUBTRACT_POLYNOMIAL":
        terms = {
            1: a * b - param(p, "d"),
            0: a * param(p, "c") + param(p, "e")
        }

    elif rule == "EXPAND_LINEAR_PRODUCT":
        terms = polynomial_multiply(
            {1: a, 0: b},
            {1: param(p, "c"), 0: param(p, "d")}
        )

    elif rule == "EXPAND_QUADRATIC_LINEAR_PRODUCT":
        terms = polynomial_multiply(
            {2: a, 1: b, 0: param(p, "c")},
            {1: param(p, "d"), 0: param(p, "e")}
        )

    else:
        raise ValueError(f"F03 未知規則：{rule}")

    return polynomial_to_string(terms)


# ============================================================
# 5. F04：函數定義域
# ============================================================

def answer_f04(rule, difficulty, p):
    """F04：函數定義域。只讀取當前規則需要的參數。"""

    if rule == "DOMAIN_LINEAR":
        return "(-∞,∞)"

    if rule == "DOMAIN_DENOMINATOR":
        b = param(p, "b")
        return f"x≠{fmt(b)}"

    if rule == "DOMAIN_SQUARE_ROOT":
        a = param(p, "a")
        return f"[{fmt(a)},∞)"

    if rule == "DOMAIN_ROOT_DENOMINATOR":
        a = param(p, "a")
        return f"({fmt(-a)},∞)"

    if rule == "DOMAIN_ROOT_AND_DENOMINATOR":
        a = param(p, "a")
        b = param(p, "b")

        if b < a:
            raise ValueError(
                "DOMAIN_ROOT_AND_DENOMINATOR 需要 b 大於或等於 a"
            )

        return (
            f"[{fmt(a)},{fmt(b)})"
            f"∪({fmt(b)},∞)"
        )

    raise ValueError(f"F04 未知規則：{rule}")

# ============================================================
# 6. F05：函數加減乘除
# ============================================================

def answer_f05(rule, difficulty, p):
    """F05：函數加減乘除。依照規則讀取必要參數。"""

    if rule == "FUNCTION_ADD_LINEAR":
        a = param(p, "a")
        b = param(p, "b")
        c = param(p, "c")
        d = param(p, "d")

        return polynomial_to_string({
            1: a + c,
            0: b + d
        })

    if rule == "FUNCTION_SUBTRACT_LINEAR":
        a = param(p, "a")
        b = param(p, "b")
        c = param(p, "c")
        d = param(p, "d")

        return polynomial_to_string({
            1: a - c,
            0: b - d
        })

    if rule == "FUNCTION_MULTIPLY_LINEAR":
        # (x+a)(bx+c)
        a = param(p, "a")
        b = param(p, "b")
        c = param(p, "c")

        return polynomial_to_string(
            polynomial_multiply(
                {1: 1, 0: a},
                {1: b, 0: c}
            )
        )

    if rule == "FUNCTION_DIVIDE_LINEAR":
        # (x+a)/(x-b)
        a = param(p, "a")
        b = param(p, "b")

        return (
            f"(x{signed_term(a)})/"
            f"(x{signed_term(-b)})，x≠{fmt(b)}"
        )

    if rule == "FUNCTION_DIVIDE_QUADRATIC_LINEAR":
        # (x²+ax+b)/(x-c)
        a = param(p, "a")
        b = param(p, "b")
        c = param(p, "c")

        numerator = polynomial_to_string({
            2: 1,
            1: a,
            0: b
        })

        return (
            f"({numerator})/"
            f"(x{signed_term(-c)})，x≠{fmt(c)}"
        )

    raise ValueError(f"F05 未知規則：{rule}")


# ============================================================
# 7. F06：函數合成
# ============================================================

def answer_f06(rule, difficulty, p):
    """F06：函數合成。依照題型規則，只讀取必要參數。"""

    if rule == "COMPOSE_LINEAR_CONSTANT":
        # f(x) = ax + b，g(x) = v
        # f(g(x)) = av + b
        a = param(p, "a")
        b = param(p, "b")
        v = param(p, "v")

        return fmt(a * v + b)

    if rule == "COMPOSE_LINEAR_LINEAR":
        # f(x) = ax + b，g(x) = cx + d
        # f(g(x)) = a(cx + d) + b
        a = param(p, "a")
        b = param(p, "b")
        c = param(p, "c")
        d = param(p, "d")

        return polynomial_to_string({
            1: a * c,
            0: a * d + b
        })

    if rule == "COMPOSE_QUADRATIC_LINEAR":
        # f(x) = x² + a，g(x) = bx + c
        # f(g(x)) = (bx + c)² + a
        a = param(p, "a")
        b = param(p, "b")
        c = param(p, "c")

        return polynomial_to_string({
            2: b**2,
            1: 2 * b * c,
            0: c**2 + a
        })

    if rule == "COMPOSE_LINEAR_QUADRATIC":
        # f(x) = ax + b，g(x) = x² + cx + d
        # f(g(x)) = a(x² + cx + d) + b
        a = param(p, "a")
        b = param(p, "b")
        c = param(p, "c")
        d = param(p, "d")

        return polynomial_to_string({
            2: a,
            1: a * c,
            0: a * d + b
        })

    if rule == "COMPOSE_QUADRATIC_QUADRATIC":
        # f(x) = ax² + bx + c，g(x) = x - d
        # f(g(x)) = a(x-d)² + b(x-d) + c
        a = param(p, "a")
        b = param(p, "b")
        c = param(p, "c")
        d = param(p, "d")

        return polynomial_to_string({
            2: a,
            1: -2 * a * d + b,
            0: a * d**2 - b * d + c
        })

    raise ValueError(f"F06 未知規則：{rule}")


# ============================================================
# 8. F07：直線方程式
# ============================================================

def answer_f07(rule, difficulty, p):
    if rule == "LINEAR_FROM_SLOPE_INTERCEPT":
        result = polynomial_to_string({
            1: param(p, "m"),
            0: param(p, "b")
        })

        return f"f(x)={result}"

    if rule in (
        "LINEAR_FROM_TWO_VALUES",
        "LINEAR_FROM_TWO_POINTS",
        "LINEAR_FROM_TWO_POINTS_GENERAL"
    ):
        x1, y1 = param(p, "x1"), param(p, "y1")
        x2, y2 = param(p, "x2"), param(p, "y2")

        if x1 == x2:
            raise ValueError("x1 與 x2 不能相同")

        m = (y2 - y1) / (x2 - x1)
        intercept = y1 - m * x1

        result = polynomial_to_string({
            1: m,
            0: intercept
        })

        if rule == "LINEAR_FROM_TWO_VALUES":
            return f"f(x)={result}"

        return f"y={result}"

    if rule == "LINEAR_FROM_SLOPE_POINT":
        m = param(p, "m")
        x1, y1 = param(p, "x1"), param(p, "y1")
        intercept = y1 - m * x1

        return "y=" + polynomial_to_string({
            1: m,
            0: intercept
        })

    raise ValueError(f"F07 未知規則：{rule}")


# ============================================================
# 9. F08：反函數
# ============================================================

def answer_f08(rule, difficulty, p):
    a, b = param(p, "a"), param(p, "b")

    if rule == "INVERSE_LINEAR":
        if a == 0:
            raise ValueError("a 不能為 0")

        return f"(x{signed_term(-b)})/{fmt(a)}"

    if rule == "INVERSE_LINEAR_REVERSED":
        # f(x)=(x-a)/b -> f^-1(x)=bx+a
        if b == 0:
            raise ValueError("b 不能為 0")

        return polynomial_to_string({
            1: b,
            0: a
        })

    if rule == "INVERSE_RATIONAL_LINEAR":
        # f(x)=(ax+b)/(x+c)
        c = param(p, "c")

        if c == 0 and a == 0:
            raise ValueError("此規格的反函數分母不可為 0")

        return (
            f"({fmt(b)}{signed_term(-c, 'x')})/"
            f"(x{signed_term(-a)})"
        )

    if rule == "INVERSE_RESTRICTED_QUADRATIC":
        # f(x)=(x-a)^2+b，原函數限制 x>=a
        return (
            f"{fmt(a)}+√(x{signed_term(-b)})，"
            f"x≥{fmt(b)}"
        )

    raise ValueError(f"F08 未知規則：{rule}")


# ============================================================
# 10. F09：一元一次方程式
# ============================================================

def answer_f09(rule, difficulty, p):
    """F09：一元一次方程式。依照題型規則讀取必要參數。"""

    if rule == "LINEAR_EQUATION_BASIC":
        # ax + b = c
        a = param(p, "a")
        b = param(p, "b")
        c = param(p, "c")

        if a == 0:
            raise ValueError("a 不能為 0")

        return equation_x((c - b) / a)

    if rule == "LINEAR_EQUATION_SUBTRACTION":
        # ax - b = c
        a = param(p, "a")
        b = param(p, "b")
        c = param(p, "c")

        if a == 0:
            raise ValueError("a 不能為 0")

        return equation_x((c + b) / a)

    if rule == "LINEAR_EQUATION_DISTRIBUTION":
        # a(x + b) = c
        a = param(p, "a")
        b = param(p, "b")
        c = param(p, "c")

        if a == 0:
            raise ValueError("a 不能為 0")

        return equation_x(c / a - b)

    if rule == "LINEAR_EQUATION_BOTH_SIDES":
        # ax + b = cx + d
        a = param(p, "a")
        b = param(p, "b")
        c = param(p, "c")
        d = param(p, "d")

        if a == c:
            raise ValueError(
                "a 與 c 不能相同，否則無法得到唯一解"
            )

        return equation_x((d - b) / (a - c))

    if rule == "LINEAR_EQUATION_FRACTIONS":
        # (ax + b)/c = (x + d)/e
        a = param(p, "a")
        b = param(p, "b")
        c = param(p, "c")
        d = param(p, "d")
        e = param(p, "e")

        if c == 0 or e == 0:
            raise ValueError("分母不能為 0")

        denominator = a * e - c

        if denominator == 0:
            raise ValueError(
                "此方程式無法得到唯一解"
            )

        numerator = c * d - b * e

        return equation_x(numerator / denominator)

    raise ValueError(f"F09 未知規則：{rule}")


# ============================================================
# 11. F10：二次方程式
# ============================================================


def answer_f10(rule, difficulty, p):
    """F10：二次方程式，支援有理數根、無理數根及無實數解。"""

    if rule == "QUADRATIC_FACTOR_MONIC":
        roots = quadratic_roots(
            1,
            param(p, "b"),
            param(p, "c")
        )

    elif rule == "QUADRATIC_FACTOR_GENERAL":
        roots = quadratic_roots(
            param(p, "a"),
            param(p, "b"),
            param(p, "c")
        )

    elif rule == "QUADRATIC_FACTOR_ALREADY_FACTORED":
        # a(x-p)(x+q)=0
        a = param(p, "a")
        p_value = param(p, "p")
        q_value = param(p, "q")

        if a == 0:
            raise ValueError("a 不能為 0")

        return two_roots(p_value, -q_value)

    else:
        raise ValueError(f"F10 未知規則：{rule}")

    # 沒有實數解
    if roots is None:
        return "無實數解"

    # 有理數根
    if roots[0] == "rational":
        return two_roots(roots[1], roots[2])

    # 無理數根：使用公式直接輸出，避免錯誤拆分正負號
    if roots[0] == "irrational":
        _, minus_b, discriminant, denominator = roots

        numerator_text = fmt(minus_b)
        discriminant_text = fmt(discriminant)
        denominator_text = fmt(denominator)

        root1 = (
            f"({numerator_text}+√({discriminant_text}))"
            f"/({denominator_text})"
        )

        root2 = (
            f"({numerator_text}-√({discriminant_text}))"
            f"/({denominator_text})"
        )

        return f"x={root1} 或 x={root2}"

    raise ValueError("F10 無法辨識二次方程式的根")



# ============================================================
# 12. F11：多項式次數
# ============================================================

def answer_f11(rule, difficulty, p):
    if rule != "POLYNOMIAL_DEGREE":
        raise ValueError(f"F11 未知規則：{rule}")

    coefficient_names = ["a", "b", "c", "d", "e", "f"]
    maximum_degree = int(difficulty)

    for degree in range(maximum_degree, -1, -1):
        name_index = maximum_degree - degree

        if name_index >= len(coefficient_names):
            continue

        name = coefficient_names[name_index]

        if name in p and param(p, name) != 0:
            return str(degree)

    raise ValueError(
        "無法判斷多項式次數，請檢查參數及題型規格"
    )


# ============================================================
# 13. F12：指數律
# ============================================================

def answer_f12(rule, difficulty, p):
    a, b = param(p, "a"), param(p, "b")

    if rule == "EXPONENT_PRODUCT":
        return f"x^{fmt(a + b)}"

    if rule == "EXPONENT_QUOTIENT":
        return f"x^{fmt(a - b)}（x≠0）"

    if rule == "EXPONENT_POWER":
        return f"x^{fmt(a * b)}"

    if rule == "EXPONENT_NEGATIVE":
        return f"x^{fmt(b - a)}（x≠0）"

    if rule == "EXPONENT_PRODUCT_POWER":
        c = param(p, "c")
        return f"x^{fmt(a * c)} y^{fmt(b * c)}"

    raise ValueError(f"F12 未知規則：{rule}")


# ============================================================
# 14. F13：根式化簡
# ============================================================

def answer_f13(rule, difficulty, p):
    if rule != "RADICAL_SIMPLIFY":
        raise ValueError(f"F13 未知規則：{rule}")

    # 目前沿用原設計：根號內常數由難度決定。
    # 若資料庫之後改用 radicand 參數，需同步修改此處。
    radicands = {
        1: 2,
        2: 3,
        3: 5,
        4: 6,
        5: 7
    }

    radicand = radicands[int(difficulty)]

    return f"{fmt(abs(param(p, 'a')))}√{radicand}"


# ============================================================
# 15. F14：提公因式
# ============================================================

def answer_f14(rule, difficulty, p):
    if rule != "FACTOR_COMMON":
        raise ValueError(f"F14 未知規則：{rule}")

    a = param(p, "a")
    d = int(difficulty)

    if d == 1:
        return f"{fmt(a)}(x+y)"

    if d == 2:
        return f"{fmt(a)}x(x+1)"

    if d == 3:
        b = param(p, "b")
        return f"({fmt(a)}+{fmt(b)})(x+y)"

    if d == 4:
        b, c = param(p, "b"), param(p, "c")
        inside = polynomial_to_string({
            2: 1,
            1: b,
            0: c
        })

        return f"{fmt(a)}({inside})"

    if d == 5:
        b, c = param(p, "b"), param(p, "c")
        inside = polynomial_to_string({
            2: 1,
            1: b,
            0: c
        })

        return f"{fmt(a)}x({inside})"

    raise ValueError(f"F14 不支援難度：{difficulty}")


# ============================================================
# 16. F15：平方差公式
# ============================================================

def answer_f15(rule, difficulty, p):
    if rule != "DIFFERENCE_OF_SQUARES":
        raise ValueError(f"F15 未知規則：{rule}")

    a = param(p, "a")
    d = int(difficulty)

    if d == 1:
        return f"(x-{fmt(a)})(x+{fmt(a)})"

    if d == 2:
        return f"(2x-{fmt(a)})(2x+{fmt(a)})"

    if d == 3:
        b = param(p, "b")
        return (
            f"({fmt(a)}x-{fmt(b)})"
            f"({fmt(a)}x+{fmt(b)})"
        )

    if d == 4:
        b = param(p, "b")
        return (
            f"({fmt(a)}x-{fmt(b)}y)"
            f"({fmt(a)}x+{fmt(b)}y)"
        )

    if d == 5:
        return (
            f"(x-{fmt(a)})(x+{fmt(a)})"
            f"(x^2+{fmt(a)}^2)"
        )

    raise ValueError(f"F15 不支援難度：{difficulty}")


# ============================================================
# 17. F16：絕對值方程式
# ============================================================

def answer_f16(rule, difficulty, p):
    if rule != "ABSOLUTE_VALUE_EQUATION":
        raise ValueError(f"F16 未知規則：{rule}")

    d = int(difficulty)

    if d == 1:
        a = param(p, "a")
        return two_roots(a, -a)

    if d == 2:
        a, b = param(p, "a"), param(p, "b")
        return two_roots(a + b, a - b)

    if d == 3:
        a, b = param(p, "a"), param(p, "b")
        return two_roots(
            (a + b) / 2,
            (a - b) / 2
        )

    if d == 4:
        a, b, c = (
            param(p, "a"),
            param(p, "b"),
            param(p, "c")
        )

        if a == 0:
            raise ValueError("a 不能為 0")

        return two_roots(
            (c - b) / a,
            (-c - b) / a
        )

    if d == 5:
        a, b, c = (
            param(p, "a"),
            param(p, "b"),
            param(p, "c")
        )

        if a == 0:
            raise ValueError("a 不能為 0")

        return two_roots(
            (c + b) / a,
            (b - c) / a
        )

    raise ValueError(f"F16 不支援難度：{difficulty}")


# ============================================================
# 18. F17：一元一次不等式
# ============================================================

def answer_f17(rule, difficulty, p):
    if rule != "LINEAR_INEQUALITY":
        raise ValueError(f"F17 未知規則：{rule}")

    a, b = param(p, "a"), param(p, "b")
    d = int(difficulty)

    if d == 1:
        # ax>b
        return solve_inequality(a, 0, ">", b)

    if d == 2:
        # ax+b>c
        return solve_inequality(
            a,
            b,
            ">",
            param(p, "c")
        )

    if d == 3:
        # ax+b<=c
        return solve_inequality(
            a,
            b,
            "<=",
            param(p, "c")
        )

    if d == 4:
        # a(x-b)>c -> ax-ab>c
        return solve_inequality(
            a,
            -a * b,
            ">",
            param(p, "c")
        )

    if d == 5:
        # (ax+b)/c >= d
        c = param(p, "c")
        right_value = param(p, "d")

        if c == 0:
            raise ValueError("分母 c 不能為 0")

        operator = ">="
        right_side = right_value * c

        if c < 0:
            operator = "<="

        return solve_inequality(
            a,
            b,
            operator,
            right_side
        )

    raise ValueError(f"F17 不支援難度：{difficulty}")


# ============================================================
# 19. F18：區間交集與聯集
# ============================================================

def interval_text(left, right, left_closed, right_closed):
    left_text = "-∞" if left is None else fmt(left)
    right_text = "∞" if right is None else fmt(right)

    left_bracket = "[" if left_closed else "("
    right_bracket = "]" if right_closed else ")"

    return (
        f"{left_bracket}{left_text},{right_text}{right_bracket}"
    )


def interval_intersection(first, second):
    l1, r1, lc1, rc1 = first
    l2, r2, lc2, rc2 = second

    if l1 is None:
        left, left_closed = l2, lc2
    elif l2 is None:
        left, left_closed = l1, lc1
    elif l1 > l2:
        left, left_closed = l1, lc1
    elif l2 > l1:
        left, left_closed = l2, lc2
    else:
        left, left_closed = l1, lc1 and lc2

    if r1 is None:
        right, right_closed = r2, rc2
    elif r2 is None:
        right, right_closed = r1, rc1
    elif r1 < r2:
        right, right_closed = r1, rc1
    elif r2 < r1:
        right, right_closed = r2, rc2
    else:
        right, right_closed = r1, rc1 and rc2

    if left is not None and right is not None:
        if left > right:
            return "∅"

        if left == right and not (
            left_closed and right_closed
        ):
            return "∅"

    return interval_text(
        left,
        right,
        left_closed,
        right_closed
    )


def interval_union(first, second):
    l1, r1, lc1, rc1 = first
    l2, r2, lc2, rc2 = second

    if l1 is None:
        first, second = first, second
    elif l2 is None:
        first, second = second, first
    elif l2 < l1:
        first, second = second, first

    fl, fr, flc, frc = first
    sl, sr, slc, src = second

    overlaps = (
        fr is None
        or sl is None
        or fr > sl
        or (fr == sl and (frc or slc))
    )

    if not overlaps:
        return (
            interval_text(fl, fr, flc, frc)
            + "∪"
            + interval_text(sl, sr, slc, src)
        )

    if fr is None or sr is None:
        right, right_closed = None, False
    elif fr > sr:
        right, right_closed = fr, frc
    elif sr > fr:
        right, right_closed = sr, src
    else:
        right, right_closed = fr, frc or src

    return interval_text(
        fl,
        right,
        flc,
        right_closed
    )


def answer_f18(rule, difficulty, p):
    """F18：區間交集與聯集。依照難度讀取必要參數。"""

    if rule not in (
        "INTERVAL_INTERSECTION",
        "INTERVAL_UNION"
    ):
        raise ValueError(f"F18 未知規則：{rule}")

    level = int(difficulty)

    if level == 5:
        # (-∞, a] 與 [b, ∞)
        a = param(p, "a")
        b = param(p, "b")

        first = (None, a, False, True)
        second = (b, None, True, False)

    else:
        # 難度 1～4 使用兩個有限區間
        a = param(p, "a")
        b = param(p, "b")
        c = param(p, "c")
        d = param(p, "d")

        if level in (1, 2):
            first = (a, b, True, True)
            second = (c, d, True, True)

        elif level == 3:
            first = (a, b, False, False)
            second = (c, d, True, True)

        elif level == 4:
            first = (a, b, True, False)
            second = (c, d, False, True)

        else:
            raise ValueError(f"F18 不支援難度：{difficulty}")

    if (
        level in (1, 3, 5)
        or rule == "INTERVAL_INTERSECTION"
    ):
        return interval_intersection(first, second)

    return interval_union(first, second)


# ============================================================
# 20. F19：有理式化簡
# ============================================================

def answer_f19(rule, difficulty, p):
    if rule != "RATIONAL_SIMPLIFY":
        raise ValueError(f"F19 未知規則：{rule}")

    a = param(p, "a")
    level = int(difficulty)

    if level == 1:
        return f"x{signed_term(a)}，x≠{fmt(a)}"

    if level == 2:
        return f"x{signed_term(a)}，x≠0"

    if level == 3:
        b = param(p, "b")
        return f"x{signed_term(b)}，x≠{fmt(-a)}"

    if level == 4:
        return f"x{signed_term(-a)}，x≠{fmt(a)}"

    if level == 5:
        simplified = polynomial_to_string({
            2: 1,
            1: a,
            0: a**2
        })

        return f"{simplified}，x≠{fmt(a)}"

    raise ValueError(f"F19 不支援難度：{difficulty}")


# ============================================================
# 21. F20：函數奇偶性
# ============================================================

def answer_f20(rule, difficulty, p):
    if rule != "FUNCTION_PARITY":
        raise ValueError(f"F20 未知規則：{rule}")

    results = {
        1: "偶函數",
        2: "奇函數",
        3: "兩者皆非",
        4: "偶函數",
        5: "兩者皆非"
    }

    return results[int(difficulty)]


# ============================================================
# 22. 主入口：供 app.py 呼叫
# ============================================================

ENGINES = {
    "F01": answer_f01,
    "F02": answer_f02,
    "F03": answer_f03,
    "F04": answer_f04,
    "F05": answer_f05,
    "F06": answer_f06,
    "F07": answer_f07,
    "F08": answer_f08,
    "F09": answer_f09,
    "F10": answer_f10,
    "F11": answer_f11,
    "F12": answer_f12,
    "F13": answer_f13,
    "F14": answer_f14,
    "F15": answer_f15,
    "F16": answer_f16,
    "F17": answer_f17,
    "F18": answer_f18,
    "F19": answer_f19,
    "F20": answer_f20,
}


def calculate_answer(type_id, difficulty, parameters, answer_rule):
    """
    計算題目標準答案。

    範例：
        calculate_answer(
            "F01",
            1,
            {"a": 2, "b": 3, "v": 4},
            "FUNCTION_VALUE_LINEAR"
        )
        -> "11"
    """

    if type_id not in ENGINES:
        raise ValueError(f"不支援的題型：{type_id}")

    if isinstance(difficulty, bool):
        raise ValueError("difficulty 必須是 1～5 的整數")

    try:
        difficulty = int(difficulty)
    except (TypeError, ValueError):
        raise ValueError("difficulty 必須是 1～5 的整數")

    if difficulty not in (1, 2, 3, 4, 5):
        raise ValueError("difficulty 必須介於 1～5")

    if not isinstance(parameters, dict):
        raise ValueError("parameters 必須是字典")

    if not isinstance(answer_rule, str) or not answer_rule.strip():
        raise ValueError("answer_rule 不可為空")

    try:
        result = ENGINES[type_id](
            answer_rule,
            difficulty,
            parameters
        )
    except (KeyError, ZeroDivisionError) as error:
        raise ValueError(
            f"{type_id} D{difficulty} 計算失敗；"
            f"answer_rule={answer_rule}；"
            f"parameters={parameters}；"
            f"原因={error}"
        ) from error

    return str(result)
