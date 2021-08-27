#!/usr/bin/env python3

from utils import dummy


# good enough for now
def lam2str(term):
    return str(term)

def do_work(term, ctx):
    print(f'{ctx}: {lam2str(term)}')

    print()


def main():
    for i, term in enumerate([
        ('LAM', 'x', 'x'),
        ('APP', ('LAM', 'x', 'x'), ('LAM', 'x', 'x')),
    ]):
        do_work(term, i)


if __name__ == '__main__':
    main()
