from collections import deque
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
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
        self._tasks_to_rexecute()

    def _tasks_to_rexecute(self):
        reexec = set()
        for tid, raw in self.nodes.items():
            new_hash = compute_hash(raw)
            cached = load_task_cache(self.wf_key, tid)
            old_hash = cached[1] if cached else None
            if new_hash != old_hash:
                reexec.add(tid)

        def collect_descendants(start):
            stack = [start]
            seen = set()
            while stack:
                node = stack.pop()
                for child in self.dag.get(node, []):
                    if child not in seen:
                        seen.add(child)
                        stack.append(child)
            return seen

        all_reexec = set(reexec)        
        for tid in list(reexec):
            all_reexec |= collect_descendants(tid)

        self.reexec = all_reexec

    def _run_single_task(self, task_id):
        raw = self.nodes[task_id]
        task = resolve_input_mappings(raw, self.results)
        cfg_hash = compute_hash(task)
        cached = load_task_cache(self.wf_key, task_id)
        if task_id not in self.reexec and cached and cached[1] == cfg_hash:
            print(f"Using cached result for task {task_id}")
            return cached[0]
        raw_output = execute_task(task)
        outputs = extract_outputs(task, raw_output)
        save_task_cache(self.wf_key, task_id, outputs, cfg_hash)
        return outputs

    def run(self):
        """
        Run the workflow without multi threading.
        """
        for task_id in self.order:
            outputs = self._run_single_task(task_id)
            self.results[task_id] = outputs
        return self.results
    
    def run_parallel(self, max_workers=4):
        """
        Run the workflow with multi threading.
        """
        indegree = {tid: 0 for tid in self.nodes}
        for parent, children in self.dag.items():
            for child in children:
                indegree[child] += 1

        ready = deque([tid for tid, deg in indegree.items() if deg == 0])
        self.results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_tid = {}

            def submit(tid):
                fut = pool.submit(self._run_single_task, tid)
                future_to_tid[fut] = tid

            for tid in ready:
                submit(tid)
            ready.clear()

            while future_to_tid:
                done, _ = wait(future_to_tid, return_when=FIRST_COMPLETED)
                for fut in done:
                    tid = future_to_tid.pop(fut)
                    try:
                        outputs = fut.result()
                    except Exception as e:
                        raise RuntimeError(f"Task {tid} failed: {e}")
                    self.results[tid] = outputs

                    for child in self.dag.get(tid, []):
                        indegree[child] -= 1
                        if indegree[child] == 0:
                            submit(child)

        return self.results
    
    def export_dag(self, output_path="workflow"):
        png_path = dag_to_dot(self.dag, filename=output_path, engine_name=self.name)
        print(f"DAG exported to {png_path}")
        return png_path
