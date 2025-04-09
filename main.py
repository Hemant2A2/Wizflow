import json
import sys
from engine import WorkflowEngine

def load_workflow_from_file(filepath):
    with open(filepath, "r") as f:
        data = json.load(f)
    if "tasks" not in data or not isinstance(data["tasks"], list):
        raise ValueError("Invalid workflow file: missing 'tasks' array")
    ids = [t["id"] for t in data["tasks"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Task IDs must be unique")
    return data

def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <workflow.json>")
        sys.exit(1)

    filepath = sys.argv[1]
    workflow_json = load_workflow_from_file(filepath)
    engine = WorkflowEngine(workflow_json)
    engine.export_dag("large_workflow_dag")
    try:
        # results = engine.run()
        results = engine.run_parallel(16)
        print("Workflow completed successfully. Results:")
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Workflow failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
