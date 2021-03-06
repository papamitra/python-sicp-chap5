#!/usr/bin/env python
# -*- coding: utf-8 -*-

from machine import *
import unittest

def fib_machine():
    mac = make_machine(['continue', 'n', 'val'],
                       {
            '-': lambda args: args[0] - args[1],
            '+': lambda args: args[0] + args[1],
            '<': lambda args: args[0] < args[1],
            },
                       """
                           (
                               (assign continue (label fib-done))
                            fib-loop
                               (test (op <) (reg n) (const 2))
                               (branch (label immediate-answer))
                               ;; Fib(n-1)を計算するように設定
                               (save continue)
                               (assign continue (label afterfib-n-1))
                               (save n)
                               (assign n (op -) (reg n) (const 1))
                               (goto (label fib-loop))
                            afterfib-n-1
                               (restore n)
                               (restore continue)
                               ;; Fib(n-2)を計算するように設定
                               (assign n (op -) (reg n) (const 2))
                               (save continue)
                               (assign continue (label afterfib-n-2))
                               (save val)
                               (goto (label fib-loop))
                            afterfib-n-2
                               (assign n (reg val))
                               (restore val)
                               (restore continue)
                               (assign val
                                       (op +) (reg val) (reg n))
                               (goto (reg continue))
                            immediate-answer
                               (assign val (reg n))
                               (goto (reg continue))
                            fib-done)
                           """
                       )
    return mac

def gcd_machine():

    def op_equal(args):
        print "op_equal: ", args
        return  args[0] == args[1]

    mac = make_machine(['a', 'b', 't'],
                           {'rem': lambda args: args[0] % args[1],
                            '=' : op_equal},
                           """
                           (test-b
                               (test (op =) (reg b) (const 0))
                               (branch (label gcd-done))
                               (assign t (op rem) (reg a) (reg b))
                               (assign a (reg b))
                              (assign b (reg t))
                               (goto (label test-b))
                            gcd-done)"""
                           )

    return mac

class TestMachine(unittest.TestCase):
    
    def setUp(self):
        pass

    def testfib(self):
        mac = fib_machine()
        set_register_contents(mac, 'n', 5)
        mac.start()
        self.assertEqual(get_register_contents(mac, 'val'), 5)

        set_register_contents(mac, 'n', 6)
        mac.start()
        self.assertEqual(get_register_contents(mac, 'val'), 8)

    def testgcd(self):
        mac = gcd_machine()

        set_register_contents(mac, 'a', 35)
        set_register_contents(mac, 'b', 49)
        
        mac.start()
        self.assertEqual(get_register_contents(mac, 'a'), 7)
        
if __name__ == '__main__':
    unittest.main()
