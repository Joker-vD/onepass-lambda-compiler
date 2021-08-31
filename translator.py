from olc_ast import lam, app, lam2str


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
    show(body(NULL, dummy), 0);
    printf("\n");
    fprintf(stderr, "heap usage: %zu\n", heap_usage);
}
''')

        return '\n'.join(self.buffer)

    def generate_show(self):
        self.append('void show(Value v, int level) {')
        self.indent()

        for term, routine_name, body_captures in self.show_data:
            inv_captures = {v: f'v.env[{k}]' for k, v in body_captures.items()}

            # Nope, you can't switch on function pointers: they are not constants becase linkers is a thing
            self.append(f'if (v.fun == {routine_name}) {{')
            self.indent()
            self.append(f'// {lam2str(term)} -- {inv_captures}')

            self.append('if (level) { printf("("); }')
            self.generate_show_meat(term, inv_captures)
            self.append('if (level) { printf(")"); }')

            self.append('return;')
            self.dedent()
            self.append('}')

        self.append(r'''fprintf(stderr, "unknown function pointer: ");
    unsigned char *funptr = (unsigned char *)&v.fun;
    for (size_t i = 0; i < sizeof(Lambda); i++) {
        fprintf(stderr, "%02x", funptr[i]);
    }
    fprintf(stderr, "\n");
    exit(1);''')

        self.append('}')
        self.dedent()

    # Uses the same idea that lam2str does, but with some meta-twists: it's not immediately obvious when you
    # should generate a recursive call to the C show() function, or call recursively generate_show_meat() itself;
    # the same goes to printing the parentheses: "level" is checked both in Python and in C code. Mind-bending!
    def generate_show_meat(self, term, inv_captures, level = 0):
        if isinstance(term, str):
            if term in inv_captures:
                # It's a captured variable, call show() recursively to print it
                self.append(f'show({inv_captures[term]}, {level});')
            else:
                self.append(f'printf("%s", "{term}");')
            return

        kind, car, cdr = term
        if kind == 'APP':
            if level > 1:
                self.append('printf("(");')

            self.generate_show_meat(car, inv_captures, 1)
            self.append('printf(" ");')
            self.generate_show_meat(cdr, inv_captures, 2)

            if level > 1:
                self.append('printf(")");')

        elif kind == 'LAM':
            if level > 0:
                self.append('printf("(");')

            self.append(f'printf("λ%s. ", "{car}");')
            self.generate_show_meat(cdr, inv_captures, 0)

            if level > 0:
                self.append('printf(")");')
        else:
            raise Exception(f'not a lambda term: {term}')

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

    # It's always either "arg_NAME" or "env[OFFSET]"", so no need for an additional temporary
    def translate_var(self, var):
        return self.lookup_var(var), []

    # If it's the current lambda's parameter, return it. Otherwise it's a captured variable: allocate
    # a slot in the closure and record this fact in the symbol table. On the next occurence of the same
    # captured variable, the recorded slot will be reused
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
        translated_param = f'arg_{mangle_for_c(param)}'

        self.enter_lambda_body(param, translated_param)

        body_captures = self.translate_lambda_body(body, routine_name, translated_param)

        self.show_data.append((term, routine_name, body_captures))

        return self.build_lambda_value(routine_name, body_captures)

    # Returns the map {offset in the environment => name of the captured variable} containing all the
    # variables captured inside the lambda's body
    def translate_lambda_body(self, body, routine_name, translated_param):
        body_value, body_stmts = self.translate_term(body)

        self.append(f'Value {routine_name}(Value* env, Value {translated_param}) {{')
        self.indent()
        self.extend(body_stmts)
        self.append(f'return {body_value};')
        self.dedent()
        self.append('}')

        return self.leave_lambda_body()

    # Takes the {offset in the environment => name of the captured variable} map and build the
    # environment according to it. Crucially, the variable lookup is performed outside of the
    # lambda's body
    def build_lambda_value(self, routine_name, body_captures):
        value = self.next_temp()

        translated_captures = [self.lookup_var(body_captures[i]) for i in range(0, len(body_captures))]

        if translated_captures:
            mem_size = f'{len(translated_captures)} * sizeof(Value)'
            env = ', '.join([
                f'(tmpenv = malloc({mem_size})',
                f'heap_usage += {mem_size}',
                *[f'tmpenv[{i}] = {c}' for i, c in enumerate(translated_captures)],
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

    # Maintaining the stack of previous environments/capture lists is the simplest way, given that we don't
    # actually need to lookup anything in the parent environments (because we are translating untyped,
    # vanilla λ-calculus). But throw in types, letrec, and uncurried functions, and you may need an actual
    # symbol table.
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

def mangle_for_c(name):
    result = ''
    for ch in name:
        if ch == '_':
            result += '_x5F'
        elif ch == '\'':
            result += '_x27'
        else:
            result += ch
    return result

def translate(term):
    # Does anybody know the "proper" way to define such helper classes? You can't really call
    # translate() second time with some other term, it's really just a one-shot context
    return Translator().translate(term)
