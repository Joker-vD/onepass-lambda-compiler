from olc_ast import lam, app

# There are lots of ways to tokenize the string, just as there are lots of ways to parse it;
# some people even managed to parse it with PCREs, but I never could remember the regex syntax
# well enough and unless someone makes gdb support regexes, I will prefer to debug the code I wrote

def is_var_start(ch):
    return ch >= 'a' and ch <= 'z' or ch == '_'

def is_var_cont(ch):
    return is_var_start(ch) or ch == "'" or ch >= '0' and ch <= '9' or ch >= 'A' and ch <= 'Z'

def is_var(token):
    return token and is_var_start(token[0])

class Tokenizer:
    def __init__(self, s, prompter):
        self.s = s
        self.prompter = prompter
        self.len = len(s)
        self.prev_pos = 0
        self.pos = 0

    def skip_ws(self):
        while self.pos < self.len and self.s[self.pos] in '\t\r\x20\v\f':
            self.pos += 1

    # All tokens are simply strings, with string 'EOF' as an end-of-input marker. It
    # works only because variables can't start with an uppercase letter.
    def next(self, continue_line=True):
        self.skip_ws()
        self.prev_pos = self.pos

        if self.pos == self.len:
            if continue_line:
                self.s = self.prompter('. ')
                self.len = len(self.s)
                self.prev_pos = 0
                self.pos = 0

                # False, so that empty input will break out. This way, I don't
                # have to muddle with handling Ctrl+C or some other key combination
                return self.next(False)
            else:
                return 'EOF'

        curr = self.pos
        look = self.s[curr]
        if is_var_start(look):
            curr += 1
            while curr < self.len and is_var_cont(self.s[curr]):
                curr += 1
        else:
            curr += 1
        word = self.s[self.pos:curr]
        self.pos = curr

        return word

# Recursive descent FTW. Again, there are lots of ways to structure it, and
# this one is somewhat unusual: there is no prev/curr or curr/peek token stored
# inside the parser, instead one token of lookahead is explicitly passed around
# to and from parse_xxx() functions.

class Parser:
    def __init__(self, init_chunk, prompter):
        self.tokenizer = Tokenizer(init_chunk, prompter)
        self.parens = 0

    def parse(self):
        term, token = self.parse_term()

        if token != 'EOF':
            raise Exception(f'Extraneous symbols at {self.tokenizer.prev_pos}')

        return term

    def parse_term(self):
        token = self.next()
        if token in 'λ\\':
            return self.parse_lambda()
        else:
            return self.parse_app(token)

    def parse_lambda(self):
        token = self.next()
        if not is_var(token):
            raise Exception(f'Expected variable after start of lambda but found {token} at {self.tokenizer.prev_pos}')
        param = token
        token = self.next()
        if token not in '.:':
            raise Exception(f'Expected "." or ":" after lambda head but found {token} at {self.tokenizer.prev_pos}')
        body, token = self.parse_term()
        return lam(param, body), token

    def parse_app(self, token):
        fun, token = self.parse_atomic(token)
        result = fun

        while is_var(token) or token == '(':
            arg, token = self.parse_atomic(token)
            result = app(result, arg)

        return result, token

    def parse_atomic(self, token):
        if token == '(':
            self.parens += 1
            result, token = self.parse_term()
            if token != ')':
                raise Exception(f'Expected ")" after parenthesized expression but found {token} at {self.tokenizer.prev_pos}')
            self.parens -= 1
            return result, self.next()

        if is_var(token):
            return token, self.next()

        raise Exception(f'expected "(" or a variable but found {token} at {self.tokenizer.prev_pos}')

    # A simple and cheap way to get multi-line input while still having [ENTER] terminating the term.
    # Python actually uses something very similar
    def next(self):
        return self.tokenizer.next(self.parens != 0)


def parse(init_chunk, prompter):
    return Parser(init_chunk, prompter).parse()
