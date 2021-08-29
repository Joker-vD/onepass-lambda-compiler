# Not much of AST, really. Variables are represented just as strings, λ-abstractions and
# applications as 3-tuples with the first element being a string discriminant. That's mighty
# enough for the languahe as simple as λ-calculus

def lam(param, body):
    return ('LAM', param, body)

def app(fun, arg):
    return ('APP', fun, arg)

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
