# One-pass λ compiler
Turning λ into C in one pass!

# Configuration

This application requires installed C compiler. Please edit function `get_cc_invocation()` inside `main.py` file if it can't find the C compiler on your system out of the box (it most likely won't unless your system is Linux with gcc).

# Usage

Enter a λ-calculus term to evaluate or a special command. Special commands are:

* `:h` — prints this help message
* `:q` — quits the program
* `:s NAME [=] λ-TERM` — adds λ-TERM to the evaluation environment under name NAME. NAME must be a valid variable name
* `:f NAME` — removes all λ-terms with name NAME from the evaluation environment
* `:l` — prints the evaluation environment
* `:o FILENAME` — reads and evaluates all lines from the file named FILENAME
* `# text...` — comment until the end of the line

The supported syntax of the λ-calculus term is this EBNF grammar:

    TERM  ::=  LAM | APP
    LAM   ::=  ('λ' | '\') VAR ('.' | ':') TERM
    APP   ::=  ATOM { ATOM }
    ATOM  ::=  VAR | '(' TERM ')'
    VAR    ~   [a-z_][a-z_A-Z0-9']*

Input of multiline terms is supported: pressing <kbd>Enter ⏎</kbd> while there are unbalanced open parentheses makes the program to expect the continuation of the input on the next line(s). Continuation lines are marked by `.` prompt instead of the normal `>` prompt. Pressing <kbd>Enter ⏎</kbd> on the continuation line without any non-whitespace input immediately aborts input.

Evaluation model is call-by-value. Before evaluating the input term, it is merged with the evaluation environment and the resulting term is evaluated instead. This merge is done using the usual let=>λ conversion, i.e., `let x = e1 in e2 => (λx. e2) e1`.

For example, the following sequence of commands:

    :s const = λk. λ_. k
    :s zero = λs. λz. z
    :s one = λs. λz. s z
    one const zero

will evaluate the term

    (λconst. (λzero. (λone. one const zero) (λs. λz. s z)) (λs. λz. z)) (λk. λ_. k)

which should result in `λ_. λs. λz. z`.

# Examples

File `std.lam` contains some example λ-terms: Church bools and pairs and, in an unexpected twist, not *Church* numbers but unsigned 8-bit-wide binary numbers instead. Only testing for zero, equality comparison, and addition — implemented with classical ripple-carry approach — are provided for those, the rest of the arithmetics is left as an exercise for the user.