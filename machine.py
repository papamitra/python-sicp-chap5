#!/usr/bin/env python
# -*- coding: utf-8 -*-

#http://inforno.net/articles/2008/09/19/sexp-library-for-python
from simplesexp import *

class Error(Exception): pass
class InvalidInstError(Error): pass
class RegisterAllocateError(Error): pass
class UnknownOperationError(Error): pass
class AllocateRegisterError(Error): pass
class BadInstructionError(Error): pass
class UnknownExpressionError(Error): pass

class Register(object):

    def __init__(self):
        self.value=None

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Stack(object):

    def __init__(self):
        self.stack=[]

    def push(self, value):
        self.stack.append(value)

    def pop(self):
        return self.stack.pop()

    def initialize(self):
        self.stack = []

def get_contents(register):
    return register.get()

def set_contents(register, value):
    register.set(value)


def make_machine(ops, controller_text):
    machine = Machine()

    machine.install_operations(ops)
    machine.install_instruction_sequence(assemble(controller_text,machine))

    return machine

class Machine(object):

    def __init__(self):

        self.register_table = {}

        self.pc = Register()
        self.register_table['pc'] = self.pc

        self.flag = Register()
        self.register_table['flag'] = self.flag

        self.stack = Stack()
        self.the_instruction_sequence = []

        self.the_ops={'initialize_stack': lambda args: self.stack.initialize()}

    def execute(self):
        while True:
            insts = get_contents(self.pc)
            print "insts: ", insts
            if insts == []: break
            proc = instruction_execution_proc(insts[0])
            proc()

        return 'done'

    def get_register(self, name):
        try:
            return self.register_table[name]
        except KeyError:
            self.allocate_register(name)
            return self.register_table[name]

    def get_stack(self):
        return self.stack
    
    def operations(self):
        return self.the_ops

    def install_instruction_sequence(self, seq):
        print "install_instruction_sequence"
        print seq
        self.the_instruction_sequence = seq

    def allocate_register(self, name):
        if self.register_table.has_key(name):
            raise AllocateRegisterError()

        self.register_table[name] = Register()

    def install_operations(self, ops):
        self.the_ops.update(ops)

    def start(self):
        set_contents(self.pc, self.the_instruction_sequence)
        self.execute()

def assemble( controller_text, machine):
    def receive(insts, labels):
        update_insts(insts, labels, machine)
        return insts

    sexps = read(controller_text)
    return extract_labels(sexps[0], receive)

def extract_labels(text, receive):
    if text == []:
        return receive([], {})
    
    def cont(insts, labels):
        next_inst = text[0]
        if type(next_inst) is Ident:
            labels.update(make_label_entry(next_inst, insts))
            return receive(insts, labels)
        else:
            return receive([make_instruction(next_inst)] + insts, labels)

    return extract_labels(text[1:], cont)

def make_label_entry(label_name, insts):
    return {label_name: insts}

def lookup_label(labels, label_name):
    return labels[label_name]

# ここで渡されるinstsは[[ 命令文, []], ...]という形をしているはず
def update_insts(insts, labels, machine):
    print """ update_insts """
    print insts
    pc = machine.get_register('pc')
    flag = machine.get_register('flag')
    stack = machine.get_stack()
    ops = machine.operations()

    def update_proc(inst):
        set_instruction_execition_proc(inst, 
                                       make_execution_procedure(instruction_text(inst), 
                                                                labels, machine, pc, flag, stack, ops))
        return inst

    map( lambda inst: update_proc(inst), insts)
        
def make_instruction(text):
    return [text, []]

def instruction_text(inst):
    return inst[0]

def instruction_execution_proc(inst):
    return inst[1]

def set_instruction_execition_proc(inst, proc):
    inst[1] = proc

def make_execution_procedure(inst, labels, machine, pc, flag, stack, ops):
    ins = inst[0]
    if ins == 'assign':
        return make_assign(inst, machine, labels, ops, pc)

    elif ins == 'test':
        return make_test(inst, machine, labels, ops, flag, pc)

    elif ins == 'branch':
        return make_branch(inst, machine, labels, flag, pc)

    elif ins == 'goto':
        return make_goto(inst, machine, labels, pc)

    elif ins == 'save':
        return make_save(inst, machine, stack, pc)

    elif ins == 'restore':
        return make_restore(inst, machine, stack, pc)

    elif ins == 'perform':
        return make_perform(inst, machine, stack, pc)
    else:
        print ins
        raise InvalidInstError

def make_assign(inst, machine, labels, ops, pc):
    def assign_reg_name(inst): return inst[1]
    def assign_value_exp(inst): return inst[2:]

    target = machine.get_register(assign_reg_name(inst))
    value_exp = assign_value_exp(inst)

    if is_operation_exp(value_exp):
        value_proc = make_operation_exp(value_exp, machine, labels, ops)
    else:
        value_proc = make_primitive_exp(value_exp[0], machine, labels)

    def assign_proc():
        set_contents(target, value_proc())
        advance_pc(pc)

    return assign_proc

def advance_pc(pc):
    print "pc:", get_contents(pc)
    set_contents(pc, get_contents(pc)[1:])

def is_operation_exp(exp):
    return is_tagged_list(exp[0], 'op')

def operation_exp_op(exp):
    return exp[0][1]

def operation_exp_operands(exp):
    return exp[1:]

def make_save(inst, machine, stack, pc):

    reg = machine.get_register(stack_inst_reg_name(inst))

    def save_proc():
        stack.push(get_contents(reg))
        advance_pc(pc)

    return save_proc

def make_restore(inst, machine, stack, pc):
    reg = machine.get_register(stack_inst_reg_name(inst))

    def restore_proc():
        set_contents(reg, stack.pop())
        advance_pc(pc)

    return restore_proc

def stack_inst_reg_name(inst):
    return inst[1]

def make_operation_exp(exp, machine, labels, operations):
    print "make_operation_exp:", exp, operations
    op = lookup_prim(operation_exp_op(exp), operations)
    aprocs = map(lambda e: make_primitive_exp(e, machine, labels),
                 operation_exp_operands(exp))

    print "op :", op
    print "aprocs: ", aprocs

    def op_proc():
        args = map(lambda p: p(), aprocs)
        print "op_proc: ", args
        return op(args)

    return lambda : op_proc()

def lookup_prim(symbol, operations):
    print "lookup_prim:", symbol
    try:        
        val = operations[symbol]
        return val
    except:
        raise UnknownOperationError()

def set_register_contents(machine, regname, content):
    set_contents(machine.get_register(regname), content)

def get_register_contents(machine, regname):
    return get_contents(machine.get_register(regname))

def make_test(inst, machine, labels, operations, flag, pc):
    print "inst is", inst
    condition = test_condition(inst)
    if is_operation_exp(condition):
        condition_proc = make_operation_exp(condition, machine, labels, operations)
        def test_proc():
            set_contents(flag, condition_proc())
            advance_pc(pc)
        return test_proc
    else:
        raise BadInstructionError()

def test_condition(test_instruction):
    return test_instruction[1:]

def make_primitive_exp(exp, machine, labels):
    print "make_primitive_exp: ", exp
    if is_constant_exp(exp):
        c = constant_exp_value(exp)
        return lambda : c

    elif is_label_exp(exp):
        insts = lookup_label(labels, label_exp_label(exp))
        return lambda : insts

    elif is_register_exp(exp):
        r = machine.get_register(register_exp_reg(exp))
        return lambda : get_contents(r)
    else:
        raise UnknownExpressionError()

def is_register_exp(exp):
    return is_tagged_list(exp, 'reg')

def register_exp_reg(exp):
    return exp[1]

def is_constant_exp(exp):
    return is_tagged_list(exp, 'const')

def constant_exp_value(exp):
    return exp[1]

def is_label_exp(exp):
    return is_tagged_list(exp, 'label')

def label_exp_label(exp):
    return exp[1]

def is_tagged_list(exp, tag):
    try:
        if exp[0] == tag:
            return True
    except:
        pass

    return False

def make_branch(inst, machine, labels, flag, pc):
    def branch_dest(branch_inst):
        return branch_inst[1]

    dest = branch_dest(inst)
    if is_label_exp(dest):
        insts = lookup_label(labels, label_exp_label(dest))
        def branch_proc():
            if get_contents(flag):
                set_contents(pc, insts)
            else:
                advance_pc(pc)

        return branch_proc
    else:
        raise BadInstructionError()

def make_goto(inst, machine, labels, pc):
    def goto_dest(goto_inst):
        return goto_inst[1]

    dest = goto_dest(inst)
    if is_label_exp(dest):
        insts = lookup_label(labels, label_exp_label(dest))
        return lambda : set_contents(pc, insts)
    elif is_register_exp(dest):
        reg = machine.get_register(register_exp_reg(dest))
        return lambda : set_contents(pc, get_contents(reg))

    raise BadInstructionError()

def make_perform(inst, machine, stack ,pc):
    def perform_action(inst):
        return inst[1:]

    action = perform_action(inst)
    if is_operation_exp(action):
        action_proc = make_operation_exp(action, machine, labels, operations)

        def perform_proc():
            action_proc()
            advance_pc(pc)

        return perform_proc
