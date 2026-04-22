import json
from backend.solver import gather_solver_input
from lambda_solver.solver_core import solve

def main():
    payload = gather_solver_input("Spring", 2027)
    print(f"Payload gathered. Courses: {len(payload.get('courses', []))}")
    result = solve(payload)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
