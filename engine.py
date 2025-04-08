from utils import (
    compute_hash,
    build_dag,
    topological_sort,
    resolve_input_mappings,
    extract_outputs,
    dag_to_dot,
)
from tasks import execute_task
from cache import load_task_cache, save_task_cache

class WorkflowEngine:
    def __init__(self, workflow_json):
        self.name    = workflow_json.get("workflow_name", "workflow")
        self.version = workflow_json.get("version", "v1")
        self.tasks   = workflow_json["tasks"]

        self.dag, indegree, self.nodes = build_dag(self.tasks)
        self.order = topological_sort(self.dag, indegree.copy())
        self.results = {}
        self.wf_key = f"{self.name}:{self.version}"

    def _run_single_task(self, task_id):
        raw = self.nodes[task_id]
        task = resolve_input_mappings(raw, self.results)
        cfg_hash = compute_hash(task)
        cached = load_task_cache(self.wf_key, task_id)
        if cached and cached[1] == cfg_hash:
            return cached[0]
        raw_output = execute_task(task)
        outputs = extract_outputs(task, raw_output)
        save_task_cache(self.wf_key, task_id, outputs, cfg_hash)
        return outputs

    def run(self):
        for task_id in self.order:
            outputs = self._run_single_task(task_id)
            self.results[task_id] = outputs
        return self.results
    
    def export_dag(self, output_path="workflow"):
        png_path = dag_to_dot(self.dag, filename=output_path, engine_name=self.name)
        print(f"DAG exported to {png_path}")
        return png_path
