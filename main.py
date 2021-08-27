#!/usr/bin/env python3

from utils import dummy


# good enough for now
def lam2str(term):
    return str(term)

def lam(param, body):
    return ('LAM', param, body)

def app(fun, arg):
    return ('APP', fun, arg)

def do_work(term, ctx):
    print(f'{ctx}: {lam2str(term)}')

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
