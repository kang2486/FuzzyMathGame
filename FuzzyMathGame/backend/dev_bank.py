"""Database-backed representative bank, separate from the team's original schema."""
import ast
import json
import operator
import os
import random
import re
from fractions import Fraction

import mysql.connector


def connect():
    return mysql.connector.connect(
        host=os.getenv('FUZZY_DB_HOST', 'localhost'),
        port=int(os.getenv('FUZZY_DB_PORT', '3306')),
        user=os.getenv('FUZZY_DB_USER', 'root'),
        password=os.environ['FUZZY_DB_PASSWORD'],
        database='fuzzy_math_game_dev', charset='utf8mb4')


def expression(source, values):
    """Only bounded numeric arithmetic; never execute database text as Python."""
    if len(source) > 200:
        raise ValueError('運算規則過長')
    ops = {ast.Add: operator.add, ast.Sub: operator.sub,
           ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow}

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            result = Fraction(node.value)
        elif isinstance(node, ast.Name) and node.id in values:
            result = Fraction(values[node.id])
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            result = visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and type(node.op) in ops:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and (right.denominator != 1 or abs(right) > 12):
                raise ValueError('次方超出範圍')
            result = ops[type(node.op)](left, int(right) if isinstance(node.op, ast.Pow) else right)
        else:
            raise ValueError('不允許的運算規則')
        if abs(result) > 10**12:
            raise ValueError('數值超出範圍')
        return result
    return visit(ast.parse(source, mode='eval').body)


def render(template, values):
    return re.sub(r'\{\{([a-zA-Z_][a-zA-Z_0-9]*)\}\}',
                  lambda match: str(values[match[1]]), template)


def catalog():
    connection = connect()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT t.chapter, t.type_id, t.name FROM question_type t '
                       'WHERE EXISTS (SELECT 1 FROM question_spec s WHERE '
                       "s.type_id=t.type_id AND s.status='published') ORDER BY t.chapter,t.type_id")
        rows = cursor.fetchall()
        chapters = {}
        for row in rows:
            chapters.setdefault(str(row['chapter']), []).append(row['type_id'])
        return chapters
    finally:
        connection.close()


def load_spec(type_id, difficulty):
    connection = connect()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM question_spec WHERE type_id=%s AND difficulty=%s AND status='published'",
                       (type_id, difficulty))
        spec = cursor.fetchone()
        if not spec:
            raise LookupError('這個題型或難度尚未發布。')
        cursor.execute('SELECT * FROM spec_parameter WHERE spec_id=%s ORDER BY parameter_name', (spec['spec_id'],))
        spec['parameters'] = cursor.fetchall()
        cursor.execute('SELECT * FROM solution_step WHERE spec_id=%s ORDER BY step_order', (spec['spec_id'],))
        steps = cursor.fetchall()
        for step in steps:
            cursor.execute('SELECT * FROM solution_option WHERE step_id=%s ORDER BY option_order', (step['step_id'],))
            step['rules'] = cursor.fetchall()
        spec['steps'] = steps
        return spec
    finally:
        connection.close()


def generate_from_spec(spec):
    values = {p['parameter_name']: Fraction(random.randint(p['min_value'], p['max_value']))
              for p in spec['parameters']}
    derived = spec['derived_values']
    for name, rule in (json.loads(derived) if isinstance(derived, str) else derived):
        values[name] = expression(rule, values)
    answer = expression(spec['answer_rule'], values)
    steps = []
    for source in spec['steps']:
        correct = expression(source['value_rule'], values)
        candidates = [(correct, True, '')]
        for rule in source['rules']:
            try:
                wrong = expression(rule['value_rule'], values)
            except (ZeroDivisionError, ValueError):
                continue
            if wrong not in [c[0] for c in candidates]:
                candidates.append((wrong, False, rule['explanation']))
        if len(candidates) < 4:
            raise ValueError(f"{spec['spec_id']} 的步驟 {source['step_order']} 缺少三個不同錯解")
        # Keep a conceptual distractor when valid, then fill with arithmetic errors.
        candidates = candidates[:4]
        options = [dict(text=render(source['display_template'], dict(values, value=value)),
                        is_correct=is_correct, explanation=explanation)
                   for value, is_correct, explanation in candidates]
        if len({o['text'] for o in options}) != 4:
            raise ValueError('選項顯示重複')
        random.shuffle(options)
        steps.append(dict(step_order=source['step_order'],
                          step_template=render(source['display_template'], dict(values, value=correct)),
                          hint=source['hint'], options=options))
    if not steps:
        raise ValueError('規格缺少解題步驟')
    answer_text = str(answer)
    if spec['type_id'] in ('D02', 'I01', 'R01', 'A01'):
        answer_text = steps[-1]['step_template']
    return dict(status='success', source='mysql_dev', source_label='MySQL 開發題庫',
                spec_id=spec['spec_id'], type_id=spec['type_id'], difficulty=spec['difficulty'],
                question_text=render(spec['question_template'], values),
                question_latex=render(spec['question_latex_template'], values),
                parameters={k: str(v) for k, v in values.items()}, answer=answer_text,
                answer_value=str(answer),
                steps=steps, total_steps=len(steps), blanks=[], total_blanks=0)


def generate(type_id, difficulty):
    return generate_from_spec(load_spec(type_id, difficulty))
