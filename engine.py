import time
import os
from collections import deque
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from utils import (
    compute_hash,
    build_dag,
    topological_sort,
    resolve_input_mappings,
    extract_outputs,
    compute_max_threads,
    dag_to_dot,
)
from tasks import execute_task
from cache import load_task_cache, save_task_cache
from store import (
    init_workflow,
    set_task_status,
    set_workflow_status,
    get_workflow_status,
)
import logging
logger = logging.getLogger(__name__)


class WorkflowEngine:
    def __init__(self, workflow_json):
        self.name    = workflow_json.get("workflow_name", "workflow")
        self.version = workflow_json.get("version", "v1")
        self.tasks   = workflow_json["tasks"]
        self.base_dir = os.path.abspath(os.path.join("runs", self.name + "_" + self.version))
        os.makedirs(self.base_dir, exist_ok=True)

        self.dag, self.indegree, self.nodes = build_dag(self.tasks)
        self.order = topological_sort(self.dag, self.indegree.copy())
        self.results = {}
        self.wf_key = f"{self.name}:{self.version}"
        init_workflow(self.wf_key, list(self.nodes.keys()))
        self._tasks_to_rexecute()

    def get_workflow_id(self):
        return self.wf_key

    def _run_single_task(self, task_id):
        self._check_paused()
        set_task_status(self.wf_key, task_id, "RUNNING")
        raw = self.nodes[task_id]
        task = resolve_input_mappings(raw, self.results)
        cfg_hash = compute_hash(task)
        cached = load_task_cache(self.wf_key, task_id)
        if task_id not in self.reexec and cached and cached[1] == cfg_hash:
            set_task_status(self.wf_key, task_id, "COMPLETED")
            logger.debug(f"Using cached result for task {task_id}")
            return cached[0]
        try:
            raw_output = execute_task(task, cwd=self.base_dir)
            outputs = extract_outputs(task, raw_output)
            save_task_cache(self.wf_key, task_id, outputs, cfg_hash)
            set_task_status(self.wf_key, task_id, "COMPLETED")
            return outputs
        except Exception as e:
            set_task_status(self.wf_key, task_id, "FAILED")
            set_workflow_status(self.wf_key, "FAILED")
            raise RuntimeError(f"Task {task_id} failed: {e}")

    def run(self):
        """
        Run the workflow without multi threading.
        """
        set_workflow_status(self.wf_key, "RUNNING")
        blocked = set()
        any_failed = False

        for task_id in self.order:
            if task_id in blocked:
                set_task_status(self.wf_key, task_id, "PENDING")
                logger.info(f"Task {task_id} blocked (ancestor failed)")
                continue
            self._check_paused()
            try:
                outputs = self._run_single_task(task_id)
                self.results[task_id] = outputs
            except Exception:
                any_failed = True
                blocked |= self._get_descendants(task_id)
        final_status = "FAILED" if any_failed else "COMPLETED"
        set_workflow_status(self.wf_key, final_status)
        return self.results
    
    def run_parallel(self, max_workers=4):
        """
        Run the workflow with multi threading.
        """
        set_workflow_status(self.wf_key, "RUNNING")
        indegree = {tid: 0 for tid in self.nodes}
        for parent, children in self.dag.items():
            for child in children:
                indegree[child] += 1

        blocked = set()
        any_failed = False
        ready = deque([tid for tid, deg in indegree.items() if deg == 0])
        self.results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_tid = {}

            def submit(tid):
                if tid in blocked:
                    set_task_status(self.wf_key, tid, "PENDING")
                    logger.info(f"Task {tid} blocked (ancestor failed)")
                else:
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
                        self.results[tid] = outputs
                    except Exception as e:
                        any_failed = True
                        blocked |= self._get_descendants(tid)

                    for child in self.dag.get(tid, []):
                        indegree[child] -= 1
                        if indegree[child] == 0:
                            submit(child)
        final_status = "FAILED" if any_failed else "COMPLETED"
        set_workflow_status(self.wf_key, final_status)
        return self.results
    
    def _tasks_to_rexecute(self):
        reexec = set()
        for tid, raw in self.nodes.items():
            new_hash = compute_hash(raw)
            cached = load_task_cache(self.wf_key, tid)
            old_hash = cached[1] if cached else None
            if new_hash != old_hash:
                reexec.add(tid)

        all_reexec = set(reexec)        
        for tid in list(reexec):
            all_reexec |= self._get_descendants(tid)

        self.reexec = all_reexec

    def _get_descendants(self, task_id):
        seen = set()
        stack = [task_id]
        while stack:
            node = stack.pop()
            for child in self.dag.get(node, []):
                if child not in seen:
                    seen.add(child)
                    stack.append(child)
        return seen
    
    def _check_paused(self):
        if get_workflow_status(self.wf_key) == "PAUSED":
            # busy‑wait until resumed
            while get_workflow_status(self.wf_key) == "PAUSED":
                time.sleep(0.5)

    def pause(self):
        set_workflow_status(self.wf_key, "PAUSED")

    def resume(self):
        if get_workflow_status(self.wf_key) == "PAUSED":
            set_workflow_status(self.wf_key, "RUNNING")

    def restart(self, from_task=None):
        if from_task is None:
            init_workflow(self.wf_key, list(self.nodes.keys()))
        else:
            queue = [from_task]
            seen = set()
            while queue:
                tid = queue.pop(0)
                if tid in seen: continue
                seen.add(tid)
                set_task_status(self.wf_key, tid, "PENDING")
                for child in self.dag.get(tid, []):
                    queue.append(child)

        set_workflow_status(self.wf_key, "PENDING")

    def estimate_max_workers(self):
        width = compute_max_threads(self.dag, self.indegree.copy())
        cpu = os.cpu_count() or 1
        return min(width, cpu * 5)
    
    def export_dag(self, output_path="workflow"):
        png_path = dag_to_dot(
            self.dag,
            all_nodes=self.nodes.keys(),
            filename=output_path,
            engine_name=self.name
        )
        return png_path
