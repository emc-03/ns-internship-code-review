#python
from operator import add, sub, mul, truediv
from functools import partial

# Define operators as a dict to map op. symbols to their functions. Non-scientific calculator only supports +, -, *, and /, so I will only include those.

_OPERATORS: dict[str, callable] ={
    '+': add,
    '-': sub,
    '*': mul,
    '/': truediv
}
 # Calculate a function that takes two numbers and an operator, checks if the op. is supported and completes the calculation. Otherwise, it will raise an error. 

def calculate(left: float, right: float, operator: str) -> float:
    fn = _OPERATORS.get(operator)
    if fn is None:
        raise ValueError("Unsupported operator.")
    if operator == "/" and right == 0:
        raise ValueError("Cannot divide by zero.")
    return fn(left, right)
