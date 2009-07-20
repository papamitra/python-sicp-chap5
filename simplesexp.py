#!/usr/bin/env python
# vim:fileencoding=utf-8
#
# simplesexp - Simple sexp reader/dumper
# Copyright (c) 2008, Yusuke Inuzuka(http://inforno.net/)
#
# License :
#   Artistic License 2.0
#

__author__  = u"Yusuke Inuzuka"
__version__ = u"0.1"
__date__    = u"2008-09-18"
__all__ = ["ParseError", "Ident","Symbol", "Pair", "Reader", "Dumper", "read", "dump", "default_binding"]
import re, sys
from unicodedata import east_asian_width
 
try:
  from re import Scanner
except ImportError:
  from sre import Scanner
 
class ParseError(StandardError): pass
 
class Ident(unicode):
  def __repr__(self):
    return "Ident(%s)"%unicode.__repr__(self)

class Symbol(unicode):
  def __repr__(self):
    return "Symbol(%s)"%unicode.__repr__(self)

class Pair(list): 
  def __repr__(self):
    return "Pair(%s)"%list.__repr__(self)

class Token(object):
  def __init__(self, value, pos):
    self.value = value
    self.pos   = pos
  def __repr__(self):
    return repr(self.value)

class Binding(object):
  def __init__(self, dct):
    self.dct = dict(((k, k.__class__), v) for k,v in dct.iteritems())
  __contains__ = lambda self, key: (key, key.__class__) in self.dct
  __getitem__  = lambda self,key:  self.dct[(key, key.__class__)]

default_binding = {"#t":True, "true":True, "#f":False, "false":False, "nil":None, "dict":Ident(u'alist->hash-table')}

class Reader(object):
  PAREN = {"]":"[", ")":"("}
  def __init__(self, binding=None, symbol_marker="'", use_dict=True):
    self.binding = binding or default_binding
    self.symbol_marker = symbol_marker
    self.use_dict = use_dict

  def read(self, value):
    self.result = []
    self.paren_stack = []
    self.source = value
    self.pos = 0
    self.quoted = False
    self.scanner = Scanner([
      (r"\s+", self("skip")),
      (r";[^\n]*\n", self("skip")),
      (r""""(((?<=\\)")|[^"])*((?<!\\)")""", self("str")),
      (r"(\(|\[)", self("open")),
      (r"(\)|\])", self("close")),
      (r"(([\d]+|(((\d+)?\.[\d]+)|([\d]+\.)))e[\+\-]?[\d]+)|(((\d+)?\.[\d]+)|([\d]+\.))", self("number")),
      (r"\-?((0x[\da-f]+)|(0[0-7]+)|([1-9][\d]*)|0)[l]?", self("number")),
      (r"""%s([^\(\[\)\]\s"]+)"""%self.symbol_marker, self("symbol")),
      (r"'", self("quote")),
      (r"""([^\(\[\)\]\s"]+)""", self("ident")),
      (r"""".*""", self("unterm_str")),
      (r".*", self("unknown_token"))
    ], re.M|re.S|re.I)
    self.scanner.scan(self.source)
    if self.paren_stack:
      self.raise_error("missing closing parenthesis.")
    return self.parse(self.result)

  def append(self, v):
    if self.quoted:
      quote_lst = self.paren_stack.pop()[1]
      quote_lst.append(Token(v, self.pos))
      self.quoted = False
    else:
      self.last().append(Token(v, self.pos))
 
  def __call__(self, name):
    def _(scanner, s):
      self.pos += len(s)
      return getattr(self, name)(s)
    return _
 
  def unknown_token(self,s): self.raise_error("unknown token: %s"%s)
  def skip(self, _): pass
  def quote(self, _):
    new_lst = []
    self.last().append(new_lst)
    self.paren_stack.append(['quote', new_lst])
    self.append(Ident('quote'))
    self.quoted = True
  def open(self, s):
      new_lst = []
      if self.quoted:
        quote_lst = self.paren_stack.pop()[1]
        quote_lst.append(new_lst)
        self.quoted = False
      else:
        self.last().append(new_lst)
      self.paren_stack.append([s, new_lst])
  def close(self, s):
      if not self.paren_stack:
        self.raise_error("missing opening parenthesis.")
      if self.PAREN[s] != self.paren_stack.pop()[0]:
        self.raise_error("missing closing parenthesis.")
  def str(self, s): self.append(eval('u""'+s+'""'))
  def unterm_str(self, s): self.raise_error("unterminated string literal.")
  def number(self, s): self.append(eval(s))
  def symbol(self, s): self.append(Symbol(s[1:]))
  def ident(self, s): 
    if s in self.binding:
      self.append(self.binding[s])
    else:
      self.append(Ident(s))

  def last(self):
    if self.paren_stack:
      return self.paren_stack[-1][1]
    else:
      return self.result
 
  def parse(self, rs):
    def is_ident(value, expected):
      return getattr(value,"value", None) == Ident(expected)
    def is_pair(rs):
      return getattr(rs, "__len__", lambda :0)()==3 and is_ident(rs[1], u".")

    if isinstance(rs, list):
      if not len(rs):
        return []
      elif self.use_dict and is_ident(rs[0], u"alist->hash-table"):
        if len(rs) != 2:
          self.raise_error("alist->hash-table: expected 1 arguments, got %d."%(len(rs)-1), rs[0].pos)
        if not all(is_pair(a) for a in rs[1]):
          self.raise_error("alist->hash-table: aruguments must be alist", rs[0].pos)
        return dict((self.parse(i[0]), self.parse(i[2])) for i in rs[1])
      elif len(rs)!=3 and any(is_ident(t, u".") for t in rs):
        self.raise_error('illegal use of "."', rs[0].pos)
      elif is_pair(rs):
        parsed = self.parse(rs[2])
        if not isinstance(rs[2], list):
          return Pair([rs[0].value, parsed])
        if isinstance(parsed, Pair):
          return Pair([rs[0].value, parsed])
        elif isinstance(parsed, list):
          return [rs[0].value]+parsed
        else:
          return [rs[0].value, parsed]
      else:
        return map(self.parse, rs)
    else:
      return rs.value
 
  def raise_error(self, msg="parse error", pos=None, range=3):
    pos = pos or self.pos
    lines = self.source.split("\n")
    curline = self.source[:pos].count("\n")
    linepos = pos - len("\n".join(lines[:curline]))
    buf = ["\n"]
    for i in xrange(max(0, curline-range), curline+1):
      buf.append("% 5d: %s"%(i+1, lines[i]))
    width = 7 + sum(east_asian_width(c) == 'W' and 2 or 1 for c in unicode(lines[i]))
    buf.append("%s~"%(" "*width))
    buf.append("line %d, %d: %s"%(curline+1,linepos, msg))
    raise ParseError(("\n".join(buf)).encode(sys.stderr.encoding))

class Dumper(object):
  def __init__(self, binding=None ,symbol_marker="'"):
    binding = binding or default_binding
    self.binding = Binding(dict(zip(binding.values(), binding)))
    self.symbol_marker = symbol_marker

  def dump(self, obj):
    result = self.to_sexp(obj, [])
    if isinstance(result, list) and len(result) and result[0]=="(":
      result = result[1:-1]
    return u" ".join(result)

  def to_sexp(self, obj, result):
    ap = result.append
    tos = lambda v: self.to_sexp(v, result)
    if isinstance(obj, Pair):
      ap("(")
      tos(obj[0])
      ap(" . ")
      tos(obj[1])
      ap(")")
    elif isinstance(obj, (tuple, list)):
      ap("(")
      map(tos, obj)
      ap(")")
    else:
      if isinstance(obj, dict):
        ap("( alist->hash-table ")
        tos([(k, Ident(u"."), v) for k,v in obj.items()])
        ap(" ) ")
      elif obj in self.binding:
        ap(unicode(Ident(self.binding[obj])))
      elif isinstance(obj, Symbol):
        ap(u"'%s"%unicode(obj))
      elif isinstance(obj, (Ident,int, float, long)):
        ap(unicode(obj))
      else:
        s = unicode(repr(obj)).decode("unicode_escape")
        m = re.match(r"""^[u|r]?["|'](.*)["|']$""", s, re.M|re.S)
        if m:
          s = m.group(1)
        ap("\"%s\""%s.replace('"','\\"').replace("\\'","'"))
    return result

dumper = Dumper()
read = Reader().read
dump = dumper.dump

#{{{ test
def test():
  def assert_eq(expect, v):
    try:
      assert expect == v
    except AssertionError:
      print u"%s \nexpected but got\n%s"%(unicode(expect), unicode(v))
  def assert_error_msg(m, s):
    try:
      m()
    except ParseError, e:
      if s not in e.message:
        raise AssertionError
      else:
        return
    raise AssertionError

  v = read(u"""
  ;comment
  (あああ hoge->fuga123 (1 . (2 . 3)) "hoge\\"hoge" ;comment2 
   foo "aaa" #t <= 'foo 
"hogehoge
foo
" (5 . (6 .()))
  )
  (dict (
    ("いいい" .
      (alist->hash-table (
        ("a-1" . "vvv")
        ("a-2" . (
          hoge foo bar 
        ))
      )))
  ))
  (10 1L -45 010 0x10 -10 -0x10 3.14 10. .001 1e100 3.14e-10 0e0)
  ; comment3 ()(
  """)
  expect = [
    [Ident(u'あああ'), Ident(u'hoge->fuga123'), Pair([1, Pair([2, 3])]), u'hoge"hoge',
     Ident(u'foo'), u'aaa', True, Ident(u'<='), Symbol(u'foo'),
     u'hogehoge\nfoo\n', [5,6]],
    {u'いいい': 
      {u'a-1': u'vvv', 
       u'a-2': [Ident(u'hoge'), Ident(u'foo'), Ident(u'bar')]}},
    [10, 1L, -45, 010, 0x10, -10, -0x10, 3.14, 10., .001, 1e100, 3.14e-10, 0e0]
  ]

  assert_eq(expect,v)
  assert_eq(expect, read(dump(v)))

  expected = Reader(use_dict=False).read(u"""
  (dict (
    (1 . 2)
    (3 . 4)
  ))
  """)
  assert_eq(expected, [[Ident(u'alist->hash-table'), [Pair([1, 2]), Pair([3, 4])]]])

  v = Reader({"T":True}, ":").read(u"""(T :hoge nil)""")
  assert_eq([True, Symbol(u"hoge"), u"nil"], v[0])
  assert_error_msg(lambda : read("(hoge () () ("), "missing closing")
  assert_error_msg(lambda : read("(hoge ) () )"), "missing opening")
  assert_error_msg(lambda : read("(hoge \"hoge 123)"), "unterminated")
  assert_error_msg(lambda : read("(dict (1 2 3) (4 5 6))"), "expected 1")
  assert_error_msg(lambda : read("(dict ((1 . 2) 3 4))"), "must be alist")
  assert_error_msg(lambda : read("(1 . 3 4 5)"), "illegal use of")

#}}} test

if __name__ == "__main__":
  test()
