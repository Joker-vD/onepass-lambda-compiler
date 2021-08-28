#!/usr/bin/env python3

from utils import put_file_contents

# No idea who invented this trick first, I've seen it in the code accompanying B. C. Pierce's TAPL;
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
        self.indentation = ''

        self.env = {}
        self.env_stack = []

        self.captures = {}
        self.captures_stack = []

        self.show_data = []

    def translate(self, term):
        self.append(r'''#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>

typedef struct Value Value;

typedef Value (*Lambda)(Value* env, Value arg);

struct Value {
    Lambda fun;
    Value* env;
};

static Value* tmpenv;
static size_t heap_usage;
''')

        self.append(f'// {lam2str(term)}')
        self.append('')

        # One way to translate top-level expression is to wrap it into a lambda with dummy parameter,
        # and then do some specific meddling with the result. Here, we *don't* generate the closure,
        # but instead check that no variables were captured.
        self.enter_lambda_body('', '_')
        top_level_captures = self.translate_lambda_body(term, 'body', '_')

        if top_level_captures:
            raise Exception(f'unbound variables: {list(map(str, top_level_captures.values()))}')

        self.generate_show()

        # I don't quite know how to handle the top-level expression better. But it's possible, of course
        self.append(r'''
Value dummy_lambda(Value* env, Value arg) {
    fprintf(stderr, "%s\n", "dummy lambda invoked");
    exit(1);
}''')

        self.append(r'''
int main(int argc, char **argv) {
    Value dummy = { .fun = dummy_lambda, .env = NULL };
    show(body(NULL, dummy));
    printf("heap usage: %zu\n", heap_usage);
}
''')

        return '\n'.join(self.buffer)

    def generate_show(self):
        self.append('void show(Value v) {')
        self.indent()

        for term, routine_name, body_captures in self.show_data:
            _, param, body = term
            inv_captures = {v: k for k, v in body_captures.items()}

            # Nope, you can't switch on function pointers: they are not constants becase linkers is a thing
            self.append(f'if (v.fun == {routine_name}) {{')
            self.indent()
            self.append(f'// {lam2str(term)} -- {inv_captures}')
            self.append(f'printf("λ%s. ", "{param}");')
            self.append('printf("\\n");')
            self.append('return;')
            self.dedent()
            self.append('}')

        self.append(r'''fprintf(stderr, "unknown function pointer: ");
    unsigned char *funptr = (unsigned char *)&v.fun;
    for (size_t i = 0; i < sizeof(Lambda); i++) {
        printf("%02x", funptr[i]);
    }
    fprintf(stderr, "\n");
    exit(1);''')

        self.append('}')
        self.dedent()

    # Returns a name of a C variable that has inside it the calculated value of the term, and the list of
    # C statements that fill that variable
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
        return self.lookup_var(var), []

    def lookup_var(self, var):
        if var in self.env:
            return self.env[var]

        closure_offset = len(self.captures)
        self.env[var] = f'env[{closure_offset}]'
        self.captures[closure_offset] = var
        return self.env[var]

    def translate_lam(self, term):
        _, param, body = term

        # Right, here things get tricky. We need to a) generate the C function *at the top-level of the file*,
        # b) generate Value with proper funptr and environment *at the current place*. And that current place
        # will generally be inside one of the other top-level functions being generated up the callstack.

        routine_name = self.next_routine()
        translated_param = f'arg_{param}'

        self.enter_lambda_body(param, translated_param)

        body_captures = self.translate_lambda_body(body, routine_name, translated_param)

        self.show_data.append((term, routine_name, body_captures))

        return self.build_lambda_value(routine_name, body_captures)

    def translate_lambda_body(self, body, routine_name, translated_param):
        body_value, body_stmts = self.translate_term(body)

        self.append(f'Value {routine_name}(Value* env, Value {translated_param}) {{')
        self.indent()
        self.extend(body_stmts)
        self.append(f'return {body_value};')
        self.dedent()
        self.append('}')

        return self.leave_lambda_body()

    def build_lambda_value(self, routine_name, body_captures):
        value = self.next_temp()

        translated_captures = [self.lookup_var(body_captures[i]) for i in range(0, len(body_captures))]

        if translated_captures:
            mem_size = f'{len(translated_captures)} * sizeof(Value)'
            env = ', '.join([
                f'(tmpenv = malloc({mem_size})',
                f'heap_usage += {mem_size}',
                *translated_captures,
                'tmpenv)'])
        else:
            env = 'NULL'

        return value, [
            f'Value {value} = {{ .fun = {routine_name}, .env = {env} }};'
        ]

    def translate_app(self, term):
        _, fun, arg = term

        fun_value, fun_stmts = self.translate_term(fun)
        arg_value, arg_stmts = self.translate_term(arg)

        value = self.next_temp()

        return value, fun_stmts + arg_stmts + [
            f'Value {value} = {fun_value}.fun({fun_value}.env, {arg_value});'
        ]

    def append(self, line):
        self.buffer.append(f'{self.indentation}{line}')

    def extend(self, lines):
        for line in lines:
            self.append(line)

    def indent(self):
        self.indentation += '\t'

    def dedent(self):
        self.indentation = self.indentation[:-1]

    def next_routine(self):
        counter = self.counter
        self.counter += 1
        result = f'lambda_{counter}'
        return result

    def next_temp(self):
        counter = self.counter
        self.counter += 1
        return f'tmp_{counter}'

    def enter_lambda_body(self, param, translated_param):
        self.env_stack.append(self.env)
        self.env = {param: translated_param}

        self.captures_stack.append(self.captures)
        self.captures = {}

    def leave_lambda_body(self):
        self.env = self.env_stack.pop()

        body_captures = self.captures
        self.captures = self.captures_stack.pop()
        return body_captures

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

    try:
        translated = translate(term)
    except Exception as e:
        print(f'Failed: {e}')
        return

    put_file_contents(f'{ctx}.c', translated)
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
        lam('x', 'y'),
        lam('x', lam('y', 'z')),
    ]):
        do_work(term, i)


if __name__ == '__main__':
    main()
