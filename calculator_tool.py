"""
calculator_tool.py  Voice Agent Calculator Tool
Uses LlamaIndex (Ollama LLM) to extract a math expression and safely evaluate it.
"""

from __future__ import annotations

import ast
import operator
import re
from typing import Optional, Tuple


_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def calculate_expression(
    user_text: str,
    model: str,
    host: str,
    api_key: Optional[str] = None,
) -> str:
    expression, error = _extract_expression_with_llamaindex(user_text, model, host, api_key)
    if not expression:
        expression = _fallback_extract_expression(user_text)

    if not expression:
        return error or "Sorry, I couldn't find a math expression to calculate."

    try:
        value = _safe_eval(expression)
    except Exception:
        return "Sorry, I couldn't evaluate that expression."

    if isinstance(value, float) and value.is_integer():
        value = int(value)

    return f"Result is {value}."


def _extract_expression_with_llamaindex(
    user_text: str,
    model: str,
    host: str,
    api_key: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    try:
        from llama_index.llms.ollama import Ollama
    except ImportError:
        return None, "LlamaIndex is not installed. Run: pip install llama-index llama-index-llms-ollama"

    client_kwargs = None
    if api_key:
        client_kwargs = {"headers": {"Authorization": f"Bearer {api_key}"}}

    try:
        if client_kwargs:
            try:
                llm = Ollama(model=model, base_url=host, client_kwargs=client_kwargs, request_timeout=30.0)
            except TypeError:
                llm = Ollama(model=model, base_url=host, request_timeout=30.0)
        else:
            llm = Ollama(model=model, base_url=host, request_timeout=30.0)
    except Exception:
        return None, "Sorry, I couldn't connect to the LLM for calculation."

    prompt = (
        "Extract the math expression from the user text.\n"
        "Rules:\n"
        "- Output ONLY the expression, no words.\n"
        "- Use digits and operators: + - * / ** ( ) % .\n"
        "- If no expression is present, output NO_EXPRESSION.\n\n"
        f"User text: {user_text}\n"
        "Expression:"
    )

    try:
        response = llm.complete(prompt)
    except Exception:
        return None, "Sorry, I couldn't parse that expression."

    raw = getattr(response, "text", None) or str(response)
    raw = raw.strip().splitlines()[0].strip()

    if not raw or "NO_EXPRESSION" in raw.upper():
        return None, None

    raw = raw.replace("^", "**")
    raw = raw.replace("\u00d7", "*")

    expression = _sanitize_expression(raw)
    return expression, None


def _fallback_extract_expression(user_text: str) -> Optional[str]:
    t = user_text.lower()
    replacements = {
        "plus": "+",
        "minus": "-",
        "times": "*",
        "into": "*",
        "multiply by": "*",
        "multiplied by": "*",
        "divide by": "/",
        "divided by": "/",
        "over": "/",
        "mod": "%",
        "modulo": "%",
        "power of": "**",
        "to the power of": "**",
        " x ": " * ",
    }

    for phrase, op in replacements.items():
        t = t.replace(phrase, f" {op} ")

    t = re.sub(r"[^0-9\+\-\*\/\%\(\)\.\sx]", " ", t)
    t = t.replace("x", "*")
    t = re.sub(r"\s+", " ", t).strip()

    expression = _sanitize_expression(t)
    return expression


def _sanitize_expression(text: str) -> Optional[str]:
    candidates = re.findall(r"[0-9\.\+\-\*\/\%\(\)\s]+", text)
    if not candidates:
        return None

    expression = candidates[0].strip()
    if not expression:
        return None

    return expression


def _safe_eval(expression: str) -> float:
    node = ast.parse(expression, mode="eval")

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.BinOp) and type(n.op) in _ALLOWED_BINOPS:
            return _ALLOWED_BINOPS[type(n.op)](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _ALLOWED_UNARYOPS:
            return _ALLOWED_UNARYOPS[type(n.op)](_eval(n.operand))
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        raise ValueError("Unsupported expression")

    return _eval(node)


if __name__ == "__main__":
    print(calculate_expression("what is 12 into 3", "llama3", "http://localhost:11434"))
