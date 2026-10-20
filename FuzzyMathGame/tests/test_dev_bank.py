"""Run against the independent dev bank; no writes, with independent math checks."""
import json
import os
from pathlib import Path
import sys
import unittest
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'backend'), str(ROOT/'database')]
from init_dev_bank import credentials
credentials()
from dev_bank import expression, generate_from_spec, load_spec, catalog
from app import app


class DevBankTests(unittest.TestCase):
    def test_arithmetic_restrictions(self):
        self.assertEqual(expression('a/3', {'a': 1}), Fraction(1,3))
        for source in ["__import__('os')", 'a.__class__', '2**100', '[1][0]']:
            with self.assertRaises(ValueError):
                expression(source, {'a': 1})

    def test_catalog(self):
        self.assertEqual(catalog(), {'1':['F09'], '2':['L01'], '3':['D02'], '4':['R01'], '5':['A01'], '6':['I01'], '7':['T01'], '8':['U01']})

    def test_4000_generated_questions(self):
        for type_id in ['F09','L01','D02','R01','A01','I01','T01','U01']:
            for difficulty in range(1,6):
                spec = load_spec(type_id,difficulty)
                for _ in range(100):
                    question = generate_from_spec(spec)
                    p = {k:Fraction(v) for k,v in question['parameters'].items()}
                    # Independent equations; derivative/integral cases verify coefficients and exponents.
                    if type_id == 'F09':
                        expected = (p['rhs']-p['b'])/p['a']
                    elif type_id == 'L01':
                        expected = p['a']*p['x']+p['b']
                    elif type_id == 'D02':
                        expected = p['a']*p['n']
                        self.assertEqual(p['power'],p['n']-1)
                        self.assertIn(f"x^({p['power']})",question['answer'])
                    elif type_id == 'I01':
                        expected = p['a']/(p['n']+1)
                        self.assertEqual(expected*p['power'],p['a'])
                        self.assertIn('+ C',question['answer'])
                    elif type_id == 'R01':
                        expected = p['a']*p['n']*p['b']+p['a']*p['b']*p['m']
                        self.assertEqual(p['power'],p['n']+p['m']-1)
                        self.assertIn(f"x^({p['power']})",question['answer'])
                    elif type_id == 'A01':
                        expected = p['b']/(2*p['a'])
                        self.assertEqual(2*p['a']*expected-p['b'],0)
                        self.assertLess(2*p['a']*(expected-1)-p['b'],0)
                        self.assertGreater(2*p['a']*(expected+1)-p['b'],0)
                        self.assertIn(f"(−∞, {expected})",question['answer'])
                    elif type_id == 'U01':
                        # Independent geometry: trapezoid with positive endpoint heights.
                        expected = (p['b']+(p['a']*p['x']+p['b']))*p['x']/2
                        self.assertGreater(expected,0)
                    else:
                        expected = p['a']*p['x']**2/2
                    self.assertEqual(Fraction(question['answer_value']),expected)
                    expected_steps = None
                    if type_id == 'R01':
                        expected_steps = [p['a']*p['n'], p['b']*p['m'], p['n']+p['m']-1, expected]
                    elif type_id == 'A01':
                        expected_steps = [2*p['a'], expected, -2*p['a'], expected]
                    elif type_id == 'U01':
                        expected_steps = [p['a']/2, expected, Fraction(0), expected]
                    if expected_steps:
                        from dev_bank import expression
                        self.assertEqual([expression(step['value_rule'], p) for step in spec['steps']], expected_steps)
                    for step in question['steps']:
                        options=step['options']
                        self.assertEqual(len(options),4)
                        self.assertEqual(sum(o['is_correct'] for o in options),1)
                        self.assertEqual(len({o['text'] for o in options}),4)
                        self.assertNotIn('{{',step['step_template'])
                        self.assertTrue(step['hint'])

    def test_apis(self):
        client=app.test_client()
        self.assertEqual(client.get('/api/game-config').json['mode'],'mysql_dev')
        for type_id in ['F09','L01','D02','R01','A01','I01','T01','U01']:
            for ability in [0,25,50,75,100]:
                response=client.get(f'/api/questions/generate-with-steps/{type_id}?ability={ability}')
                self.assertEqual(response.status_code,200,response.json)
                self.assertEqual(response.json['source'],'mysql_dev')
        for suffix in ['?ability=nan','?difficulty=0','?ability=101']:
            self.assertEqual(client.get('/api/questions/generate-with-steps/F09'+suffix).status_code,400)
        self.assertEqual(client.get('/api/questions/generate-with-steps/F99?difficulty=1').status_code,404)


if __name__ == '__main__':
    unittest.main(verbosity=2)
