"""Produce portable seed SQL with fixed, self-authored representative templates."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def quote(value):
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace('\\', '\\\\').replace("'", "''") + "'"


def build():
    rows = []
    def insert(table, values):
        rows.append(f"INSERT INTO {table} VALUES ({','.join(map(quote, values))});")
    insert('bank_meta', (1, 'FuzzyMathGame representative development bank v1'))
    chapters = [(1,'函數與數學基礎'),(2,'極限與連續'),(3,'微分的基本概念'),
                (4,'微分法則'),(5,'微分的應用'),(6,'不定積分'),(7,'定積分'),(8,'積分的應用')]
    for row in chapters:
        insert('chapter', row)
    # Formula templates use {{name}}, leaving normal LaTeX braces intact.
    definitions = [
        ('F09',1,'一元一次方程式','解方程式 {{a}}x + {{b}} = {{rhs}}。',
         r'{{a}}x+{{b}}={{rhs}}', [['rhs','a*x+b']], 'x',
         [('兩邊減去 {{b}}：{{rhs}} − {{b}} = {{value}}','rhs-b','移項時兩邊做相同運算。','rhs+b'),
          ('兩邊除以 {{a}}：x = {{product}} ÷ {{a}} = {{value}}','x','消去係數要除以係數。','product*a')]),
        ('L01',2,'多項式極限','求一次多項式在指定點的極限。',
         r'\lim_{x\to {{x}}}({{a}}x+{{b}})', [], 'a*x+b',
         [('多項式連續，代入 x={{x}}，先算 {{a}} × {{x}} = {{value}}','a*x','多項式在所有實數連續，可以直接代入。','a+x'),
          ('加上常數項：{{product}} + {{b}} = {{value}}','a*x+b','代入後仍需保留常數項。','a*x-b')]),
        ('D02',3,'冪次函數微分','求下列函數的導數。',
         r'f(x)={{a}}x^{ {{n}} }', [['power','n-1']], 'a*n',
         [('冪次法則：係數 {{a}} × 指數 {{n}} = {{value}}','a*n','使用 d(xⁿ)/dx = nxⁿ⁻¹。','a+n'),
          ('新指數：{{n}} − 1 = {{value}}','n-1','微分後指數要減一。','n+1'),
          ('導數 f′(x) = {{value}} · x^({{power}})','a*n','將新係數與新指數合併。','a')]),
        ('I01',6,'冪次函數不定積分','求下列不定積分，答案包含積分常數 C。',
         r'\int {{a}}x^{ {{n}} }\,dx', [['a','k*(n+1)'],['power','n+1']], 'k',
         [('積分後指數：{{n}} + 1 = {{value}}','n+1','冪次積分先將指數加一；此題 n 為正整數。','n-1'),
          ('新係數：{{a}} ÷ {{power}} = {{value}}','a/(n+1)','係數須除以新指數，不是原指數。','a/n'),
          ('不定積分 = {{value}} · x^({{power}}) + C','k','最後一定要加積分常數 C。','a')]),
        ('T01',7,'一次函數定積分','計算下列定積分。',
         r'\int_0^{ {{x}} } {{a}}t\,dt', [['a','2*k'],['upper','k*x**2']], 'k*x**2',
         [('先積分，新指數：1 + 1 = {{value}}','2','先找原函數，再代上下限。','1'),
          ('原函數 F(t) = {{value}} · t²','a/2','一次項積分後係數要除以 2。','a*2'),
          ('上限 F({{x}}) = {{k}} × {{x}}² = {{value}}','k*x**2','上限代入原函數，注意平方。','k*x'),
          ('定積分 F({{x}}) − F(0) = {{upper}} − 0 = {{value}}','k*x**2','定積分是上限值減下限值，不加 C。','-upper')])]
    definitions += [
        ('R01',4,'乘法微分法則','請依乘法法則求導數，先分別微分兩因子，再合併。',
         r'f(x)=({{a}}x^{ {{n}} })({{b}}x^{ {{m}} })',
         [['power','n+m-1']], 'a*b*(n+m)',
         [('第一因子微分的係數：{{a}} × {{n}} = {{value}}','a*n','乘法法則為 (uv)′ = u′v + uv′。先求 u′。','a+n'),
          ('第二因子微分的係數：{{b}} × {{m}} = {{value}}','b*m','再求 v′，原本的 u 和 v 不可同時丟掉。','b+m'),
          ('兩項合併後的 x 指數：{{n}} + {{m}} − 1 = {{value}}','n+m-1','u′v 和 uv′ 的指數相同，都是 n+m−1。','n*m'),
          ('f′(x) = {{value}} · x^({{power}})','a*b*(n+m)','係數相加為 abn+abm，不是只將兩個導數相乘。','a*n*b*m')]),
        ('A01',5,'二次函數的遞增遞減區間','判斷下列函數的遞增、遞減區間。係數 a 為正數。',
         r'f(x)={{a}}x^2-{{b}}x+{{k}}',
         [['critical','b/(2*a)'],['left','b/(2*a)-1']], 'b/(2*a)',
         [('f′(x) = {{value}}x − {{b}}','2*a','先微分，常數項的導數為 0。','a'),
          ('令 f′(x)=0，臨界點 x = {{value}}','b/(2*a)','解 2ax−b=0，得到 x=b/(2a)。','-b/(2*a)'),
          ('左側測試點 x={{left}} 的導數值 = {{value}}','2*a*left-b','左側導數為負，函數遞減；右側導數為正。','2*a*left+b'),
          ('遞減區間 (−∞, {{value}})，遞增區間 ({{value}}, +∞)','b/(2*a)','開口向上的拋物線在臨界點左減右增，端點不含入開區間。','-b/(2*a)')]),
        ('U01',8,'曲線與座標軸面積','求直線與 x 軸、左右邊界所圍面積。區間內函數皆為正。',
         r'y={{a}}t+{{b}},\quad 0\le t\le {{x}}',
         [['upper','a*x**2/2+b*x']], 'a*x**2/2+b*x',
         [('原函數 F(t) = {{value}} · t² + {{b}}t','a/2','區間內函數為正，面積等於定積分。先找原函數。','a*2'),
          ('代入上限 F({{x}}) = {{value}}','a*x**2/2+b*x','一次項和常數項的積分都要代入上限。','a*x**2/2+b'),
          ('代入下限 F(0) = {{value}}','0','每項含 t，因此 t=0 時原函數值為 0。','b'),
          ('面積 A = F({{x}}) − F(0) = {{value}} 平方單位','a*x**2/2+b*x','幾何面積必須非負；本題整段在 x 軸上方。','-upper')])]
    for type_id, chapter, title, question, latex, derived, answer, steps in definitions:
        insert('question_type',(type_id,chapter,title))
        for difficulty in range(1,6):
            spec_id=f'{type_id}_DEV_D{difficulty}'
            derived_values=[*derived,['product','a*x']]
            insert('question_spec',(spec_id,type_id,difficulty,question,latex,
                   json.dumps(derived_values),answer,'published',
                   '本次自編代表題；五級目前僅調整參數範圍，非完整認知難度分級。'))
            for name,low,high in [('a',2,3+difficulty),('b',1,3+difficulty),
                                  ('x',2,3+difficulty),('k',2,3+difficulty),('n',2,min(5,2+difficulty)),('m',2,min(4,2+difficulty))]:
                insert('spec_parameter',(spec_id,name,low,high))
            for order,(display,value,hint,wrong) in enumerate(steps,1):
                step_id=f'{spec_id}_S{order}'
                insert('solution_step',(step_id,spec_id,order,display,value,hint))
                rules=[(wrong,'CONCEPT','檢查運算法則、符號或代入順序。'),
                       (f'({value})+1','ARITHMETIC_PLUS_ONE','計算結果多了 1。'),
                       (f'({value})-1','ARITHMETIC_MINUS_ONE','計算結果少了 1。'),
                       (f'({value})+2','ARITHMETIC_PLUS_TWO','重新核對計算結果。'),
                       (f'({value})-2','ARITHMETIC_MINUS_TWO','重新核對計算結果。')]
                for option_order,(rule,code,explanation) in enumerate(rules,1):
                    insert('solution_option',(step_id,option_order,rule,code,explanation))
    migration = [row for row in rows if any(f"('{prefix}" in row for prefix in ('R01','A01','U01'))]
    migration.append("INSERT INTO bank_meta VALUES (2, 'Representative chapters 4, 5, 8');")
    (ROOT/'migration_002.sql').write_text('USE fuzzy_math_game_dev;\nSTART TRANSACTION;\n'+'\n'.join(migration)+'\nCOMMIT;\n',encoding='utf-8')
    insert('bank_meta', (2, 'Representative chapters 4, 5, 8'))
    (ROOT/'seed.sql').write_text('USE fuzzy_math_game_dev;\nSTART TRANSACTION;\n'+'\n'.join(rows)+'\nCOMMIT;\n',encoding='utf-8')


if __name__ == '__main__':
    build()
    print('Created seed.sql: 8 types, 40 parameter-range specifications')
