"""Independent practice bank; not a recovery of the original MySQL data."""
import random

TYPE_IDS = ["F01", "F02", "F03", "F04"]

def step(label, value, hint, mistakes=()):
    wrong = []
    for candidate in [*mistakes, value + 1, value - 1, -value, value + 2, value + 3]:
        if candidate != value and candidate not in wrong:
            wrong.append(candidate)
    text = f"{label} = {value}"
    return {"step_template": text, "hint": hint,
            "options": [{"text": text, "is_correct": True}] + [
                {"text": f"{label} = {v}", "is_correct": False} for v in wrong[:3]]}

def generate(type_id, difficulty):
    if type_id not in TYPE_IDS:
        raise LookupError("本機練習題庫目前提供 F01 到 F04。")
    a = random.randint(2, 3 + difficulty)
    b = random.randint(1, 3 + difficulty)
    c = random.randint(-5, -1)
    x = random.randint(2, 3 + difficulty)
    if type_id == "F01":
        answer = a*x+b
        question = f"已知 f(x) = {a}x + {b}，求 f({x})。"
        steps = [step(f"代入後先計算 {a} × {x}", a*x, "先把 x 換成指定的數值，再做乘法。", [a+x]),
                 step(f"f({x}) = {a*x} + {b}", answer, "乘法完成後加上常數項。", [a*x-b, a*(x+b)])]
    elif type_id == "F02":
        answer = a*x*x+b*x+c
        question = f"已知 f(x) = {a}x² + {b}x + ({c})，求 f({x})。"
        steps = [step(f"先計算 {x}²", x*x, "平方是自己乘自己，不是乘以 2。", [2*x]),
                 step(f"二次項 {a} × {x*x}", a*x*x, "先算次方，再乘係數。", [(a*x)**2]),
                 step(f"一次項 {b} × {x}", b*x, "一次項也要代入 x。", [b+x]),
                 step(f"合併 {a*x*x} + {b*x} + ({c})", answer, "負常數相加等同減去其絕對值。", [a*x*x+b*x-c, a*x*x-b*x+c])]
    elif type_id == "F03":
        answer = a*x+b
        question = f"已知 f(t) = {a}t + {b}、g(x) = x + ({c})，求 f(g({x}))。"
        inner = x+c
        answer = a*inner+b
        steps = [step(f"先求內層 g({x}) = {x} + ({c})", inner, "合成函數由內向外計算。", [x-c]),
                 step(f"將內層結果乘以 {a}：{a} × ({inner})", a*inner, "把整個 g(x) 當作 f 的輸入。", [a*x+c]),
                 step(f"最後加上常數 {b}：{a*inner} + {b}", answer, "外層函數的常數項也要保留。", [a*inner-b])]
    else:
        answer = x
        rhs = a*x+b
        question = f"解方程式 {a}x + {b} = {rhs}。"
        steps = [step(f"兩邊減去 {b}，右邊 {rhs} − {b}", rhs-b, "移項時兩邊要做相同的運算。", [rhs+b]),
                 step(f"兩邊除以 {a}，x = {rhs-b} ÷ {a}", answer, "消去係數要用除法。", [(rhs-b)*a, rhs-b-a])]
    for i, item in enumerate(steps, 1):
        item["step_order"] = i
        random.shuffle(item["options"])
    return dict(status="success", source="local_practice", source_label="本機練習題庫", type_id=type_id,
                difficulty=difficulty, question_text=question, question_latex="", answer=answer,
                steps=steps, total_steps=len(steps), blanks=[], total_blanks=0)
