import json
import uvicorn
from fastapi import FastAPI
from sympy.parsing.latex import parse_latex
from sympy import Symbol
from sympy.core import Add, Mul, Pow, Function, Number
from pylatexenc.latexwalker import (
    LatexWalker,
    LatexMacroNode,
    LatexGroupNode,
    LatexCharsNode,
    LatexMathNode
)

app = FastAPI()
# =======================
# SymPy → AST
# =======================

def sympy_to_ast(expr):
    if isinstance(expr, Number):
        return {"type": "number", "value": float(expr)}

    if isinstance(expr, Symbol):
        return {"type": "symbol", "name": str(expr)}

    if isinstance(expr, Add):
        return {
            "type": "add",
            "args": [sympy_to_ast(arg) for arg in expr.args]
        }

    if isinstance(expr, Mul):
        return {
            "type": "mul",
            "args": [sympy_to_ast(arg) for arg in expr.args]
        }

    if isinstance(expr, Pow):
        base, exp = expr.args
        return {
            "type": "pow",
            "base": sympy_to_ast(base),
            "exp": sympy_to_ast(exp)
        }

    if isinstance(expr, Function):
        return {
            "type": "func",
            "name": expr.func.__name__,
            "args": [sympy_to_ast(arg) for arg in expr.args]
        }

    return {
        "type": "unknown",
        "repr": str(expr)
    }

# =======================
# LaTeX token AST (fallback)
# =======================

OPERATORS = {
    "+", "-", "*", "/", "=", "<", ">", 
    r"\ne", r"\times", r"\leqslant", r"\leq", r"\geqslant", 
    r"\geq", r"\approx", r"\propto", r"\Rightarrow", r"\rightarrow",
    r"\supset", r"\Leftrightarrow", r"\wedge", r"\vee", r"\neg",
    r"\forall", r"\exists", r"\varnothing", r"\notin", r"\subseteq",
    r"\subset", r"\supseteq", r"\subsetneq", r"\supsetneq",
    r"\setminus", r"\cap", r"\cup", r"\to", r"\mapsto"
}

FUNCTIONS = {
    r"\sin", r"\cos", r"\tan", r"\cot", r"\arcsin",
    r"\arccos", r"\arctan", r"\arccot", r"\sinh",
    r"\cosh", r"\tanh", r"\coth", r"\sec", r"\csc",
    r"\sqrt", r"\frac", r"\cfrac"
}

def latex_nodes_to_ast(nodes):
    ast = []

    for node in nodes:
        if isinstance(node, LatexMacroNode):
            name = "\\" + node.macroname
            ast.append({
                "type": "macro",
                "name": name,
                "args": latex_nodes_to_ast(
                    sum(
                        [arg.nodelist for arg in node.nodeargd.argnlist if arg],
                        []
                    )
                ) if node.nodeargd else []
            })

        elif isinstance(node, LatexGroupNode):
            ast.append({
                "type": "group",
                "children": latex_nodes_to_ast(node.nodelist)
            })

        elif isinstance(node, LatexMathNode):
            ast.append({
                "type": "math",
                "children": latex_nodes_to_ast(node.nodelist)
            })

        elif isinstance(node, LatexCharsNode):
            for ch in node.chars:
                if not ch.isspace():
                    ast.append({
                        "type": "char",
                        "value": ch
                    })

    return ast

def latex_to_token_ast(latex: str):
    walker = LatexWalker(latex)
    nodes, _, _ = walker.get_latex_nodes()
    return {
        "type": "latex_token_ast",
        "children": latex_nodes_to_ast(nodes)
    }

@app.post("/latex_to_ast")
async def latex_to_ast(latex: str):
    try:
        expr = parse_latex(latex)
        return {
            "mode": "semantic",
            "ast": sympy_to_ast(expr)
        }
    except Exception:
        return {
            "mode": "syntactic",
            "ast": latex_to_token_ast(latex)
        }



# 2 + ответы каждого этапа
# in json ast + парм количество шагов решения если -1 = решение до конца если 2 два шага 

# a + b + c
# a + b * c
# x^2 + y^3
# \sin(x) + \cos(y)
# \sin(x^2) + \cos(y^3)
# \frac{a+b}{c+d}