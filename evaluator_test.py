#!/usr/bin/env python
# -*- coding:utf-8 -*-

from evaluator import *
from simplesexp import *
import unittest

class TestEvaluator(unittest.TestCase):
    
    def setUp(self):
        pass

    def test_isselfeval(self):
        self.assertTrue(is_self_evaluating(3))
        self.assertTrue(is_self_evaluating(3000000000000000))
        self.assertTrue(is_self_evaluating(3000000000000.1234))
        self.assertTrue(is_self_evaluating('test'))

    def test_isvariable(self):
        self.assertTrue(is_variable(Symbol('a')))

    def test_isquoted(self):
        self.assertTrue(is_quoted(read("'(1 2 3)")[0]))

    def test_isassignment(self):
        self.assertTrue(is_assignment(read("(set! a 1)")[0]))

    def test_isdefinition(self):
        self.assertTrue(is_definition(read("(define (testfunc a b) a + b)")[0]))

    def test_isif(self):
        self.assertTrue(is_if(read("(if (eq? 1 1) #t #f)")[0]))

    def test_islambda(self):
        self.assertTrue(is_lambda(read("(lambda (a b) (+ a b))")[0]))

    def test_isbegin(self):
        self.assertTrue(is_begin(read("(begin (+ 1 2) (+ 3 4))")[0]))

    def test_isapplication(self):
        self.assertFalse(is_application(read("'a")[0]))
        self.assertTrue(is_application(read("(+ a b)")[0]))

    def test_lookup_variable_value(self):
        self.assertEqual(1 , lookup_variable_value('a', [{'a': 2}, {'a': 1}]))
        self.assertEqual(2 , lookup_variable_value('a', [{'a': 2}, {'b': 1}]))
        self.assertRaises(VariableUnassignedError, lookup_variable_value, 'c', [{'a': 2}, {'b': 1}])

    def test_text_of_quotation(self):
        self.assertEqual([1, 2, 3], text_of_quotation([Ident(u'quote'), [1, 2, 3]]))
        
    def test_first_operand(self):
        self.assertEqual(Ident(u'a'),
                         first_operand(read("(a b c)")[0]))

    def test_is_last_operand(self):
        self.assertFalse(is_last_operand(read("(a b c)")))
        self.assertTrue(is_last_operand([]))

    def test_empty_arglist(self):
        mac = make_machine(['argl'],
                           ops,
                           """(
                             (assign argl (op empty-arglist))
                           )""")
        mac.start()

        self.assertEqual(get_register_contents(mac, 'argl'), [])
        
    def test_arglist(self):
        mac = make_machine(['argl'],
                           ops,
                           """(
                             (assign argl (op empty-arglist))
                             (assign argl (op adjoin-arg) (const 1) (reg argl))
                             (assign argl (op adjoin-arg) (const 2) (reg argl))
                           )""")
        mac.start()

        self.assertEqual(get_register_contents(mac, 'argl'), [1,2])

    def test_rest_operands(self):
        mac = make_machine(['argl','a'],
                           ops,
                           """(
                             (assign argl (op empty-arglist))
                             (assign argl (op adjoin-arg) (const 1) (reg argl))
                             (assign argl (op adjoin-arg) (const 2) (reg argl))
                             (assign a (op rest-operands) (reg argl))
                           )""")
        mac.start()

        self.assertEqual(get_register_contents(mac, 'a'), [2])

    def test_is_primitive_procedure(self):
        mac = make_machine(['exp'],
                           ops,
                           """(
                             (assign exp (op empty-arglist))
                             (assign exp (op adjoin-arg) (const 'primitive) (reg exp))
                             (assign exp (op adjoin-arg) (const 'test-func) (reg exp))
                             (test (op primitive-procedure?) (reg exp))
                           )""")
        mac.start()

        self.assertEqual(get_register_contents(mac, 'flag'), 1)
        
    def test_is_compound_procedure(self):
        mac = make_machine(['exp'],
                           ops,
                           """(
                             (assign exp (op empty-arglist))
                             (assign exp (op adjoin-arg) (const 'procedure) (reg exp))
                             (assign exp (op adjoin-arg) (const 'test-func) (reg exp))
                             (test (op compound-procedure?) (reg exp))
                           )""")
        mac.start()

        self.assertEqual(get_register_contents(mac, 'flag'), 1)

    def test_apply_primitive_procedure(self):
        mac = make_machine(['val'],
                           ops,
                           """(
                             (assign val (op apply-primitive-procedure)
                                         (const ('primitive +))
                                         (const 1) (const 2) (const 3) (const 4))
                           )""")
        mac.start()
        self.assertEqual(get_register_contents(mac, 'val'), 10)

    
    def test_extend_environment(self):
        mac = make_machine(['proc', 'unev', 'env', 'argl'],
                           ops,
                           """(
                            (assign proc (const ('procedure (x y z) (+ x y z) ()) ))
                            (assign argl (const (1 2 3)))
                            (assign unev (op procedure-parameters) (reg proc))
                            (assign env (op procedure-environment) (reg proc))
                            (assign env (op extend-environment)
                                        (reg unev) (reg argl) (reg env))
                           )""")
        mac.start()
        self.assertEqual(get_register_contents(mac, 'env'), [{Ident(u'x'):1, Ident(u'y'):2, Ident(u'z'):3}])

    def test_set_variable_value(self):
        mac = make_machine(['proc', 'unev', 'env', 'argl'],
                           ops,
                           """(
                            (assign proc (const ('procedure (x y z) (+ x y z) ()) ))
                            (assign argl (const (1 2 3)))
                            (assign unev (op procedure-parameters) (reg proc))
                            (assign env (op procedure-environment) (reg proc))
                            (assign env (op extend-environment)
                                        (reg unev) (reg argl) (reg env))
                            (assign proc (const ('procedure (a b c) (+ a b c) ()) ))
                            (assign argl (const (1 2 3)))
                            (assign unev (op procedure-parameters) (reg proc))
                            (assign env (op extend-environment)
                                        (reg unev) (reg argl) (reg env))
                            (perform (op set-variable-value!) (const 'a) (const -1) (reg env))
                           )""")
        mac.start()
        self.assertEqual(get_register_contents(mac, 'env'), [{Ident(u'a'):-1, Ident(u'b'):2, Ident(u'c'):3}, \
                                                                 {Ident(u'x'):1, Ident(u'y'):2, Ident(u'z'):3}])

    def test_definition(self):
        mac = make_machine(['val', 'unev', 'env'],
                           ops,
                           """(
                             (assign env (const ((dict ((a . 2))))))
                             (assign unev (const a))
                             (assign val (const 1))
                             (perform (op define-variable!) (reg unev) (reg val) (reg env))
                           )""")
        mac.start()
        self.assertEqual(get_register_contents(mac, 'env'), [{Ident(u'a'):1}])

    def _test_prompt_for(self):
        mac = make_machine(['exp'],
                           ops,
                           """(
                             (perform (op prompt-for-input) (const "test"))
                             (assign exp (op read))
                           )""")
        mac.start()
        self.assertEqual(get_register_contents(mac, 'exp'), "test input")

if __name__ == '__main__':
    unittest.main()
