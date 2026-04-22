"""
AWS Lambda entry point for the TES solver.
"""
import json
from solver_core import solve


def lambda_handler(event, context):
    """
    Receives the solver payload from the backend, runs the solver, returns the result.
    Lambda will JSON-serialize the return value automatically.
    """
    # event may already be a dict (Lambda console test) or a JSON string
    payload = event if isinstance(event, dict) else json.loads(event)
    return solve(payload)
