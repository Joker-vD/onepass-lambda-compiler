from olc_ast import lam, app


def is_var_start(ch):
    return ch >= 'a' and ch <= 'z' or ch == '_'

def is_var_cont(ch):
    return is_var_start(ch) or ch == "'" or ch >= '0' and ch <= '9' or ch >= 'A' and ch <= 'Z'

def is_var(token):
    return token and is_var_start(token[0])

class Tokenizer:
    def __init__(self, s):
        self.s = s
        self.len = len(s)
        self.prev_pos = 0
        self.pos = 0

    def skip_ws(self):
        while self.pos < self.len and self.s[self.pos] in '\t\r\x20\v\f':
            self.pos += 1

    def next(self, continue_line=True):
        self.skip_ws()
        self.prev_pos = self.pos

        if self.pos == self.len:
            if continue_line:
                self.s = input('. ')
                self.len = len(self.s)
                self.prev_pos = 0
                self.pos = 0
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

class Parser:
    def __init__(self, init_chunk):
        self.tokenizer = Tokenizer(init_chunk)
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

    def next(self):
        return self.tokenizer.next(self.parens != 0)


def parse(init_chunk):
    return Parser(init_chunk).parse()
