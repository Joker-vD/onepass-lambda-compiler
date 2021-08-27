#!/usr/bin/env python3

from utils import put_file_contents

# no idea who invented this trick first, I've seen it in the code accompanying B. C. Pierce's TAPL
# basically, you kinda track what priority level the expression you're about to print has, and put parens
# around it if it's low enough to need it. Here, level 0 is "either top or a body of a lambda", level 1 is
# "lhs of the application", and level 2 is "rhs of an application". Variables never need parens, lambdas
# need parens if they're being applied from whatever side, and applications need parens only when they're
# on the rhs of another application
def lam2str(term, level=0):
    if isinstance(term, str):
        return term

    kind, car, cdr = term
    if kind == 'LAM':
        result = f'λ{car}. {lam2str(cdr, 0)}'
        if level > 0:
            result = f'({result})'
        return result

    if kind == 'APP':
        result = f'{lam2str(car, 1)} {lam2str(cdr, 2)}'
        if level > 1:
            result = f'({result})'
        return result

    raise Exception(f'not a lambda term: {term}')


def lam(param, body):
    return ('LAM', param, body)

def app(fun, arg):
    return ('APP', fun, arg)


# Gonna need some context
class Translator:
    def __init__(self):
        self.counter = 0
        self.buffer = []

    def translate(self, term):
        self.append(r'''#include <stdio.h>
#include <stdlib.h>

typedef struct Value Value;

typedef Value (*Lambda)(Value* env, Value arg);

struct Value {
    Lambda fun;
    Value* env;
};

#define LOOKUP(v) v
#define MAKE_ENV(how) 0
''')

        self.append(f'// {lam2str(term)}')

        self.append('''
Value body(void) {''')

        self.append(f'return {self.translate_term(term)};')

        self.append(r'''}

void show(Value v) {
    printf("%d\n", v);
}

int main(int argc, char **argv) {
    show(body());
}
''')

        return '\n'.join(self.buffer)

    # Returns a name of a C variable that has inside it the calculated value of the term
    def translate_term(self, term):
        if isinstance(term, str):
            return self.translate_var(term)

        kind, car, cdr = term
        if kind == 'LAM':
            return self.translate_lam(term)

        if kind == 'APP':
            return self.translate_app(term)

        raise Exception(f'not a lambda term: {term}')

    def translate_var(self, var):
        return f'LOOKUP({var})'

    def translate_lam(self, term):
        _, param, body = term

        # Right, here things get tricky. We need to a) generate the C function *at the top-level of the file*,
        # b) generate Value with proper funptr and environment *at the current place*. And that current place
        # will generally be inside one of the other top-level functions being generated up the callstack.

        routine_name = self.next_lambda()

        self.append(f'// generate {routine_name} with bound {param}')
        value = self.translate_term(body)
        self.append(f'// ended generating {routine_name}')

        self.append('Value tmp;')
        self.append(f'tmp.fun = {routine_name};')
        self.append(f'tmp.env = MAKE_ENV(HOW);')

        return 'tmp'

    def translate_app(self, term):
        _, fun, arg = term

        self.append('Value tmp;')
        self.append(f'tmp = fun_value.fun(fun_value.env, arg);')

        return 'tmp'

    def append(self, line):
        self.buffer.append(line)

    def next_lambda(self):
        counter = self.counter
        self.counter += 1
        return f'lambda_{counter}'

def translate(term):
    # Does anybody know the "proper" way to define such helper classes? You can't really call
    # translate() second time with some other term, it's really just a one-shot context
    return Translator().translate(term)

def compile_and_run(c_filename):
    # Technically, I could try to use $CC, but do *you* have it set in your environment? If
    # yes, please let everyone on the Internet know. Anyway, just put in here whatever invocation
    # works on your machine
    import os, subprocess

    basename, _ = os.path.splitext(c_filename)
    obj_filename = f'{basename}.obj'
    exe_filename = f'{basename}.exe'

    cmd = ' '.join([
        r'"D:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat" && cl.exe /O2',
        c_filename,
        f'/link /out:{exe_filename}'
    ])
    p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print('Running:')
    try:
        subprocess.run([os.path.join('.', exe_filename)])
    except Exception as e:
        print(f'Failed: {e}')
        return

    os.remove(obj_filename)
    os.remove(exe_filename)

def do_work(term, ctx):
    print(ctx)
    print(lam2str(term))
    put_file_contents(f'{ctx}.c', translate(term))
    compile_and_run(f'{ctx}.c')

    print()


def main():
    for i, term in enumerate([
        lam('x', 'x'),
        app(lam('x', 'x'), lam('x', 'x')),
        lam('y', app(lam('x', 'x'), lam('x', 'x'))),
        lam('z', lam('y', lam('x', app(app('x', 'y'), 'z')))),
        app(lam('z', lam('y', lam('x', app(app('x', 'y'), 'z')))), lam('t', app(app('t', 't'), 't'))),
        app(app(lam('z', lam('y', lam('x', app('z', app('y', 'x'))))), lam('t', app('t', app('t', 't')))), lam('t', 't')),
    ]):
        do_work(term, i)


if __name__ == '__main__':
    main()
