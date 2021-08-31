# One-pass λ-to-C compiler

It turns λ-terms into C programs **in just one pass**! Well, there is still some output buffering, but that's inevitable: during the translation of e.g. `(λx. x (λy. y) (λz. z) x)`, translation of `λy. y` starts before translation of `λx. ...` is completed, and C doesn't support nested functions, so one of those has to be done in a side buffer.

But other than that, it *is* a one-pass compiler: a λ-term is traversed exactly once and the C code is emitted immediately during this traversal; no intermediate representations are built, closure-conversion and lambda-hoisting are dealt with on the fly.

## Installation

Requires at least Python 3.6.5 and a C compiler.

    git clone https://github.com/Joker-vD/onepass-lambda-compiler.git
    cd onepass-lambda-compiler
    ./main.py

## Configuration

This application requires an installed C compiler, to compile produced C files. Please edit function `get_cc_invocation()` inside `main.py` file if it can't find the C compiler on your system out of the box (it most likely won't unless your system is Linux with gcc).

## Usage

Enter a λ-calculus term to evaluate, or a special command. Special commands are:

* `:h` — prints this help message
* `:q` — quits the program
* `:s NAME [=] λ-TERM` — adds λ-TERM to the evaluation environment under name NAME. NAME must be a valid variable name
* `:es NAME [=] λ-TERM` — evaluates λ-TERM and add the result to the evaluation environment under name NAME. NAME must be a valid variable name
* `:f NAME` — removes all λ-terms with name NAME from the evaluation environment
* `:ff` — removes all λ-terms from the evaluation environment
* `:l` — prints the evaluation environment
* `:o FILENAME` — reads and evaluates all lines from the file named FILENAME

The supported syntax of the λ-calculus term is this EBNF grammar:

    TERM  ::=  LAM | APP
    LAM   ::=  ('λ' | '\') VAR ('.' | ':') TERM
    APP   ::=  ATOM { ATOM }
    ATOM  ::=  VAR | '(' TERM ')'
    VAR    ~   [a-z_][a-z_A-Z0-9']*

Comments are started by `#` symbol and extend until the end of the line. Input of multiline terms is supported: pressing <kbd>Enter ⏎</kbd> while there are unbalanced open parentheses makes the program expect the continuation of the input on the next line(s). Continuation lines are marked by `.` prompt instead of the normal `>` prompt.

Evaluation model is call-by-value. Before the input term is evaluated, it is merged with the evaluation environment and the resulting term is evaluated instead. This merge is done using the usual let=>λ conversion, i.e., `let x = e1 in e2  =>  (λx. e2) e1`.

For example, the following sequence of commands:

    :s const = λk. λ_. k
    :s zero = λs. λz. z
    :s one = λs. λz. s z
    one const zero

will evaluate the term

    (λconst. (λzero. (λone. one const zero) (λs. λz. s z)) (λs. λz. z)) (λk. λ_. k)

which should result in `λ_. λs. λz. z`.

## Examples

File `std.lam` contains some example λ-terms: Church bools and pairs and, in an unexpected twist, not *Church* numbers but unsigned 8-bit-wide binary numbers instead. Only zero testing, equality comparison, and addition — implemented with classical ripple-carry approach — are provided for those, the rest of the arithmetics is left as an exercise for the user.

Fibonacci series is provided as an example of a recursive function. Instead of using a Y combinator (which I still maintain to be a device of dubious practical value), it was written using what essentially is closure conversion plus escaping/known function splitting.

## Why though

Two weeks ago I made a throwaway comment on HN: "translating between closely related languages is often like this: the mapping between their constructs is 1-to-1 and almost trivial. But try translating e.g. λ-calculus into C in one go, without separate lambda-lifting/closure-converting steps: it's absolutely doable but quite messy".

But how messy *exactly* is this? Turns out, the answer is "actually, not even that messy". I believe it's mainly because untyped, pure λ-calculus is a very tiny language.

## Futher notes

See `NOTES.md` and comments in the code for explanation and description of some implementation choices. The code was structured in the most straightforward way (this is subjective, of course) which means it defines way fewer classes than one would normally expect. There isn't even a class for a symbol table because there is not much to store in one of those!

But this whole task does not need lots of supporting data structures to solve it, not really (the `translator.py` file that has the actual logic is less than 300 lines), and since I actually knew how to solve it, I just sat and wrote it in two evenings. Two more evenings went into writing and polishing the REPL, wrting the help message and these notes and comments because those things seemed more useful and important than turning small, straightforward procedural code into medium-to-large, intricate OOP-web of interdependent classes.