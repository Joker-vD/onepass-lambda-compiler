#!/usr/bin/env python3

from utils import dummy


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

typedef Value int;

Value body(void) {''')

        self.append(self.translate_term(term))

        self.append(r'''}

void show(Value v) {
    printf("%d\n", v);
}

int main(int argc, char **argv) {
    show(body());
}''')

        return '\n'.join(self.buffer)

    def translate_term(self, term):
        return '\treturn 0;'

    def append(self, line):
        self.buffer.append(line)

def translate(term):
    # Does anybody know the "proper" way to define such helper classes? You can't really call
    # translate() second time with some other term, it's really just a one-shot context
    return Translator().translate(term)

def do_work(term, ctx):
    print(ctx)
    print(lam2str(term))
    print(translate(term))

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
