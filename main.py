#!/usr/bin/env python3

import os

from utils import put_file_contents, get_file_contents, chop, delete_file
from olc_ast import lam, app, lam2str
from olc_parser import is_var, parse
from translator import translate


def get_cc_invocation(c_filename):
    # Technically, I could try to use $CC, but do *you* have it set in your environment? If
    # yes, please let everyone on the Internet know. Anyway, just put in here whatever invocation
    # works on your machine
    basename, _ = os.path.splitext(c_filename)
    obj_filename = f'{basename}.obj'
    exe_filename = f'{basename}.exe'

    if os.name == 'nt':
        cmd = ' '.join([
            r'"D:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat" && cl.exe /O2',
            c_filename,
            f'/link /out:{exe_filename}'
        ])
        use_shell = True
    else:
        cmd = ['gcc', '-o', exe_filename, c_filename]
        use_shell = False

    return cmd, use_shell, obj_filename, exe_filename

def compile_and_run(c_filename):
    import subprocess

    cmd, use_shell, obj_filename, exe_filename = get_cc_invocation(c_filename)
    p = subprocess.run(cmd, shell=use_shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if p.returncode != 0:
        raise Exception(f'compilation failed: {p.stdout}\n{p.stderr}')

    try:
        p = subprocess.run([os.path.join('.', exe_filename)], stdout=subprocess.PIPE)
    finally:
        delete_file(obj_filename)
        delete_file(exe_filename)

    return p.stdout.decode()

def translate_compile_run(term, ctx, keep_c_file):
    translated = translate(term)
    c_filename = f'{ctx}.c'
    put_file_contents(c_filename, translated)
    try:
        return compile_and_run(c_filename)
    finally:
        if not keep_c_file:
            delete_file(c_filename)

def do_test(term, ctx):
    print(ctx)
    print(lam2str(term))

    try:
        result = translate_compile_run(term, ctx, True)
    except Exception as e:
        print(f'Failed: {e}')
    else:
        print(result)


def test_run():
    const = lam('k', lam('_', 'k'))
    church_succ = lam('n', lam('s', lam('z', app('s', app(app('n', 's'), 'z')))))
    church_pred = lam('n', lam('s', lam('z', app(app(app('n', lam('g', lam('h', app('h', app('g', 's'))))), app(const(), 'z')), lam('t', 't')))))
    church_zero = lam('s', lam('z', 'z'))
    church_four = lam('s', lam('z', app('s', app('s', app('s', app('s', 'z'))))))

    for i, term in enumerate([
        lam('x', 'x'),
        app(lam('x', 'x'), lam('x', 'x')),
        lam('y', app(lam('x', 'x'), lam('x', 'x'))),
        lam('z', lam('y', lam('x', app(app('x', 'y'), 'z')))),
        app(lam('z', lam('y', lam('x', app(app('x', 'y'), 'z')))), lam('t', app(app('t', 't'), 't'))),
        app(app(lam('z', lam('y', lam('x', app('z', app('y', 'x'))))), lam('t', app('t', app('t', 't')))), lam('t', 't')),
        lam('x', 'y'),
        lam('x', lam('y', 'z')),
        app(church_pred, church_four),
        app(app(app(church_pred, church_four), church_succ), church_zero),
    ]):
        do_test(term, i)


# A very simple REPL, what else to say? The command parser could have been a bit more
# prinicipled, but if you haven't noticed yet, this project tries to not overbuild anything
class Interaction:
    def __init__(self):
        self.should_quit = False
        self.defs = []
        self.input_buffer = ''

    def interact(self):
        import sys

        while not self.should_quit:
            try:
                s = self.input('> ')
                self.parse_cmd(s)
            except EOFError:
                self.cmd_quit('')
            except Exception as e:
                print(f'Failed: {e}', file=sys.stderr)

        print('Goodbye!')

    def parse_cmd(self, s):
        s = s.lstrip()

        if s == '' or s.startswith('#'):
            return

        if s.startswith("?"):
            self.cmd_help('')
            return

        if s.startswith(":"):
            cmd, s = chop(s[1:])

            if cmd == 'q':
                self.cmd_quit(s)
            elif cmd == 's':
                self.cmd_set_macro(s)
            elif cmd == 'l':
                self.cmd_list_macros(s)
            elif cmd == 'f':
                self.cmd_forget_macro(s)
            elif cmd == 'o':
                self.cmd_execute_file(s)
            elif cmd == 'h':
                self.cmd_help(s)
            else:
                raise Exception(f'unknown command: {cmd}. Try ":h" for help')
        else:
            self.cmd_eval_and_print_term(parse(s, self.input))

    def cmd_eval_and_print_term(self, term):
        print(lam2str(term))
        print(self.eval_term(term))

    def cmd_quit(self, s):
        self.should_quit = True

    def cmd_set_macro(self, s):
        name, s = chop(s)
        if not is_var(name):
            raise Exception(f'invalid name: {name}')
        if s.startswith('='):
            s = s[1:]
        self.defs.append((name, parse(s, self.input)))

    def cmd_list_macros(self, s):
        for name, term in self.defs:
            print(f'{name} = {lam2str(term)}')

    def cmd_forget_macro(self, s):
        name = s
        for i in reversed(range(0, len(self.defs))):
            if self.defs[i][0] == name:
                self.defs[i:] = self.defs[i+1:]

    def cmd_execute_file(self, s):
        filename = s
        data = get_file_contents(filename)
        self.input_buffer += data
        if not data.endswith('\n'):
            self.input_buffer += '\n'

    def cmd_help(self, s):
        print('One-pass λ compiler')
        print()
        print('Enter a λ-calculus term to evaluate or a special command. Special commands are:')
        print('\t• :h — prints this help message')
        print('\t• :q — quits the program')
        print('\t• :s NAME [=] λ-TERM — adds λ-TERM under name NAME to the evaluation environment. NAME must be a valid variable name')
        print('\t• :f NAME — removes all λ-terms with name NAME from the evaluation environment')
        print('\t• :l — prints the evaluation environment')
        print('\t• :o FILENAME — reads and evaluates all lines from the file named FILENAME')
        print('\t• # text... — comment until the end of the line')
        print()
        print('The supported syntax of the λ-calculus term is this EBNF grammar:')
        print('\tTERM  ::=  LAM | APP')
        print('\tLAM   ::=  (\'λ\' | \'\\\') VAR (\'.\' | \':\') APP')
        print('\tAPP   ::=  ATOM { ATOM }')
        print('\tATOM  ::=  VAR | \'(\' TERM \')\'')
        print('\tVAR    ~   [a-z_][a-z_A-Z0-9\']*')
        print()
        print('Input of multiline terms is supported: pressing [ENTER ⏎] while there are unbalanced open parentheses makes the program'
            ' to expect the continuation of the input on the next line(s). Continuation lines are marked by "." prompt instead of the normal'
            ' ">" prompt. Pressing [ENTER ⏎] on the continuation line without any non-whitespace input immediately aborts input.')
        print()
        print('Evaluation model is call-by-value. Before evaluating the input term, it is merged with the evaluation environment and the'
            ' resulting term is evaluated instead. This merge is done using the usual let=>λ conversion, i.e., let x = e1 in e2 => (λx. e2) e1.'
            ' For example, the following sequence of commands:')
        print('\t:s const = λk. λ_. k')
        print('\t:s zero = λs. λz. z')
        print('\t:s one = λs. λz. s z')
        print('\tone const zero')
        print('will evaluate the term')
        print('\t(λconst. (λzero. (λone. one const zero) (λs. λz. s z)) (λs. λz. z)) (λk. λ_. k)')
        print('which should result in λ_. λs. λz. z')

    def eval_term(self, term):
        full_term = self.build_full_term(term)
        return translate_compile_run(full_term, 'tmp', True)

    def build_full_term(self, term):
        result = term
        for name, term in reversed(self.defs):
            result = app(lam(name, result), term)
        return result

    def input(self, prompt):
        if not self.input_buffer:
            return input(prompt)

        nl_offset = self.input_buffer.find('\n')
        if nl_offset == -1:
            result = self.input_buffer
            self.input_buffer = ''
            return result

        result = self.input_buffer[:nl_offset]
        self.input_buffer = self.input_buffer[nl_offset+1:]
        return result

def interactive_run():
    try:
        import readline
    except ModuleNotFoundError:
        pass

    Interaction().interact()


def main():
    #test_run()
    interactive_run()


if __name__ == '__main__':
    main()
