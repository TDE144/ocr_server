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

def evaluate_step_by_step(expr):
    """Выполняет пошаговое вычисление выражения, где это возможно"""
    steps = []
    
    if isinstance(expr, Number):
        # Число - конечный результат
        return [float(expr)]
    
    if isinstance(expr, Symbol):
        # Символ нельзя вычислить
        return [str(expr)]
    
    if isinstance(expr, Add):
        
        args_results = [evaluate_step_by_step(arg) for arg in expr.args]
        
        max_steps = max(len(r) for r in args_results)
        for i in range(max_steps):
            step_args = []
            for j, arg_results in enumerate(args_results):
                if i < len(arg_results):
                    step_args.append(arg_results[i])
                else:
                    step_args.append(arg_results[-1])
            
            
            current_expr = Add(*[parse_latex(str(arg)) if isinstance(arg, str) else arg 
                               for arg in step_args])
            
            try:
                evaluated = current_expr.evalf()
                if evaluated != current_expr:
                    steps.append(str(evaluated))
                else:
                    steps.append(str(current_expr))
            except:
                steps.append(str(current_expr))
        
        return steps
    
    if isinstance(expr, Mul):
        # Для умножения
        args_results = [evaluate_step_by_step(arg) for arg in expr.args]
        
        max_steps = max(len(r) for r in args_results)
        for i in range(max_steps):
            step_args = []
            for j, arg_results in enumerate(args_results):
                if i < len(arg_results):
                    step_args.append(arg_results[i])
                else:
                    step_args.append(arg_results[-1])
            
            current_expr = Mul(*[parse_latex(str(arg)) if isinstance(arg, str) else arg 
                               for arg in step_args])
            
            try:
                evaluated = current_expr.evalf()
                if evaluated != current_expr:
                    steps.append(str(evaluated))
                else:
                    steps.append(str(current_expr))
            except:
                steps.append(str(current_expr))
        
        return steps
    
    if isinstance(expr, Pow):
        # Для степени
        base_results = evaluate_step_by_step(expr.args[0])
        exp_results = evaluate_step_by_step(expr.args[1])
        
        max_steps = max(len(base_results), len(exp_results))
        for i in range(max_steps):
            base = base_results[i if i < len(base_results) else -1]
            exp = exp_results[i if i < len(exp_results) else -1]
            
            current_expr = Pow(
                parse_latex(str(base)) if isinstance(base, str) else base,
                parse_latex(str(exp)) if isinstance(exp, str) else exp
            )
            
            try:
                evaluated = current_expr.evalf()
                if evaluated != current_expr:
                    steps.append(str(evaluated))
                else:
                    steps.append(str(current_expr))
            except:
                steps.append(str(current_expr))
        
        return steps
    
    if isinstance(expr, Function):
        # Для функций
        args_results = [evaluate_step_by_step(arg) for arg in expr.args]
        
        max_steps = max(len(r) for r in args_results)
        for i in range(max_steps):
            step_args = []
            for j, arg_results in enumerate(args_results):
                if i < len(arg_results):
                    step_args.append(arg_results[i])
                else:
                    step_args.append(arg_results[-1])
            
            
            func_type = type(expr)
            current_expr = func_type(*[parse_latex(str(arg)) if isinstance(arg, str) else arg 
                                     for arg in step_args])
            
            try:
                evaluated = current_expr.evalf()
                if evaluated != current_expr:
                    steps.append(str(evaluated))
                else:
                    steps.append(str(current_expr))
            except:
                steps.append(str(current_expr))
        
        return steps
    
    # Для неизвестных типов
    return [str(expr)]


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


@app.post("/latex_to_ast_with_steps")
async def latex_to_ast_with_steps(latex: str):
    try:
        expr = parse_latex(latex)
        ast_result = sympy_to_ast(expr)
        steps = evaluate_step_by_step(expr)
        
        return {
            "mode": "semantic",
            "ast": ast_result,
            "steps": steps,
            "original": latex,
            "final_result": steps[-1] if steps else str(expr)
        }
    except Exception as e:
        return {
            "mode": "syntactic",
            "ast": latex_to_token_ast(latex),
            "steps": [],
            "original": latex,
            "final_result": latex,
            "error": str(e)
        }
