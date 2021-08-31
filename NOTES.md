### Value representation

In λ-calculus the only values are functions. We will represent them as fat function pointers:

    typedef struct Value Value;

    typedef Value (*Lambda)(Value* env, Value arg);

    struct Value {
        Lambda fun;
        Value* env;
    };

Technically, the typedef for `Lambda` could be inlinded: we don't need typecasts at the callsites because all generated C functions will have exactly this type. But if we tried to support functions with several parameters we'd have to cast them to function types with correct number of arguments: otherwise, it'd be UB.

Notice that `Lambda` only get the environment (the array with the values of the captured variables), not the whole closure. No cheap `letrec`, but helps with the text ordering.

### Lambda ordering

If you look at 3.c (at this commit right now), you'l see that nested lambdas actually already are being generrated in mostly correct order:

    // λz. λy. λx. x y z

    Value body(void) {
    // generate lambda_0 with bound z
    // generate lambda_1 with bound y
    // generate lambda_2 with bound x
    Value tmp;
    tmp = fun_value.fun(fun_value.env, arg);
    // ended generating lambda_2
    Value tmp;
    tmp.fun = lambda_2;
    tmp.env = MAKE_ENV(HOW);
    // ended generating lambda_1
    Value tmp;
    tmp.fun = lambda_1;
    tmp.env = MAKE_ENV(HOW);
    // ended generating lambda_0
    Value tmp;
    tmp.fun = lambda_0;
    tmp.env = MAKE_ENV(HOW);
    return tmp;
    }

Outermost lambda `λz. ...` is `lambda_0`, and it's value-closure is being filled in at the very end.

### Capturing variables

It's actually surprisingly simple: during the translation of a nested lambda's body, whenever a variable is accessed that is *not* this nested lambda's parameter, record that it should be translated as `env[CAPTURED_VARIABLES_COUNTER]`, and increment the `CAPTURED_VARIABLES_COUNTER`, and re-resolve it. After the body is translated, restore the outer lambda's list of captured variables and resolve every variable from the nested lambda's list.

Probably a picture would be better:

    λz. λy. λx. x y z
    ^   ^   ^   -----
    |   |   |
    |   |   |-- lambda_2
    |   |-- lambda_1
    |-- lambda_0

Let's translate the body of `lambda_2`: we start with the empty list of captured variables `[]`, translate `x` as `arg_x`, then `y` as `env[0]`, and `z` produces `env[1]`, plus after it's done, we have recorded the list `[y, z]`.

Now we're translating the body `lambda_1`: we start with the empty list of captured variables `[]`, and re-resolve variables from the list `[y, z]`. translating `y` produces `arg_y`, and translating `z` produces `env[0]`: yes, `[0]`. So the resulting environment is `{arg_y, env[0]}`, and the list of captured variables is `[z]`.

Now we're translating the body `lambda_0`: we start with the empty list of captured variables `[]`, and re-resolve variables from the list `[z]`. Translating `z` produces `arg_z`. So the resulting environment is `{arg_z}`, and the list of captured variables is `[]`.

So the full code looks something like this:

    Value lambda_2(Value* env, Value arg_x) {
        Value tmp_xy = arg_x.fun(arg_x.env, env[0]);
        Value tmp_xyz = tmp_xy.fun(tmp_xy.env, env[1]);
        return tmp_xyz;
    }

    Value lambda_1(Value* env, Value arg_y) {
        Value result = { .fun = lambda_2, env = {arg_y, env[0]} };
        return result;
    }

    Value lambda_0(Value* env, Value arg_z) {
        Value result = { .fun = lambda_1, env = {arg_z} };
        return result;
    }

So if you read from bottom to top, `lambda_0` puts `arg_z` at `env[0]` for `lambda_1`, then `lambda_1` puts `env[0]` from *its* `env` at `env[1]` for `lambda_2`, so when `lambda_2` accesses `env[1]`, it actually accesses the value of `arg_z` from `lambda_0`, as intended. Whew!

Notice how we *don't* pre-calculate the free variables: we instead record and assign them closure slots on the fly.

### Printing closure values

Generating code for printing the closure values as λ-terms with captured substituted in is similar in spirit to the `lam2str()` function. Interestingly enough, we don't need to α-convert anything because of the call-to-value semantics: the captured variables reference the closures which are, well, closed. For example, value `λx. x y z + {y: λx. x + {}, z: λk. k x + {x: λx. x + {}}` should be printed as `λx. x (λx. x) (λk. k (λx. x))`. It's somewhat confusing but still correct and unambiguous for a careful enough reader. Of course, we could also have just mangled names, e.g. uniformly turning `x` into `x@lambda_11`, or carefully tracking the bound variables and appending numbers or primes, but eh.

Since modern optimizing C compilers have the "function deduplication" optimization, the result of evaluating `(λx. x) (λy. y)` may be printed either as `(λx. x)` or as `(λy. y)`: the generated functions `lambda_0` and `lambda_1` have identical machine code, so the optimizer throws one of them away and uses the other one everywhere. This among other things means that e.g. all 2-element unions (`Bool = True | False`, `SwitchState = Off | On`, etc.) when encoded with Scott–Mogensen encoding will be indistinguishable at run time. A more extreme example is that functions

    Value f(Value a) { return a; }
    Value g(Value a, Value b, Value c) { return a; }

may actually have the same address. That makes m- and n-tuples *sometimes* distinguishable at run time, and *sometimes* not.

I am writing all this so that if another poor soul for some reason would decide to implement a toy functional language with Scott–Mogensen encoding used for data representation, they would not spend several hours trying to figure out whether the GC corrupts the heap, or the debugging print somehow miscompares function pointers, or they have just gone insane (after all, they've actually decided to use Scott–Mogensen encoding, so...). No, it's just your C compiler waltzing with UB: the standard severely under-restricts how the function pointers behave.

### Parsing lambdas

It's recursive descent, but with support for line continuations inside the lexer! Nothing special, although can be tricky to debug: I'm particularly prone to accidentally writing infinite loops in such parsers for some reason.

Also, the exact grammar implemented does *not* support `\x. x \t. t` as an acceptable input equivalent to `\x. x (\t. t)`, but it can be done by changing `parse_atomic()` to expect lambda in addition to the left parenthesis and variables.
