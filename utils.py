import json
import hashlib
from collections import defaultdict, deque
from jsonpath_ng import parse
from graphviz import Digraph

def compute_hash(obj):
    normalized = json.dumps(obj, sort_keys=True).encode("utf‑8")
    return hashlib.sha256(normalized).hexdigest()

def build_dag(tasks):
    dag = defaultdict(list)
    dag = { t["id"]: [] for t in tasks }
    indegree = {}
    nodes = {}

    for t in tasks:
        tid = t["id"]
        nodes[tid] = t
        indegree.setdefault(tid, 0)

    for t in tasks:
        tid = t["id"]
        for parent in t.get("depends_on", []):
            if parent not in nodes:
                raise ValueError(f"Task '{tid}' depends on unknown '{parent}'")
            dag[parent].append(tid)
            indegree[tid] = indegree.get(tid, 0) + 1

    return dag, indegree, nodes

def topological_sort(dag, indegree):
    q = deque([n for n,deg in indegree.items() if deg == 0])
    order = []
    while q:
        node = q.popleft()
        order.append(node)
        for child in dag.get(node, []):
            indegree[child] -= 1
            if indegree[child] == 0:
                q.append(child)
    if len(order) != len(indegree):
        raise RuntimeError("Cycle detected in workflow graph")
    return order

def resolve_input_mappings(task, results):
    import copy
    t = copy.deepcopy(task)
    context = {}
    for parent in t.get("depends_on", []):
        parent_outs = results.get(parent, {})
        for key, val in parent_outs.items():
            if key in context:
                pass
            context[key] = val
    for var, val in context.items():
        placeholder = f"{{{{{var}}}}}"
        for field in ("command", "url"):
            if field in t and isinstance(t[field], str):
                t[field] = t[field].replace(placeholder, str(val))
        if "headers" in t:
            for k, v in t["headers"].items():
                if isinstance(v, str):
                    t["headers"][k] = v.replace(placeholder, str(val))
        if "body" in t:
            body_str = json.dumps(t["body"])
            body_str = body_str.replace(placeholder, str(val))
            t["body"] = json.loads(body_str)
    return t

def extract_outputs(task, raw_output):
    outputs = {}
    for name, spec in task.get("outputs", {}).items():
        typ = spec.get("type")
        if typ == "json":
            expr = parse(spec["json_path"])
            matches = [m.value for m in expr.find(raw_output)]
            outputs[name] = matches[0] if matches else None
        elif typ == "file":
            outputs[name] = spec["path"]
        else:
            outputs[name] = raw_output
    return outputs

def dag_to_dot(dag, all_nodes, filename="workflow.dot", engine_name=None):
    dot = Digraph(comment=engine_name or "Workflow DAG", format="png")
    for node in all_nodes:
        dot.node(node, node)
    for parent, children in dag.items():
        for child in children:
            dot.edge(parent, child)
    dot.save(filename)
    dot.render(filename, view=False)
    return filename + ".png"

def compute_max_threads(dag, indegree):
    from collections import deque
    indeg = indegree.copy()
    frontier = deque([n for n, d in indeg.items() if d == 0])
    max_width = len(frontier)

    while frontier:
        next_frontier = []
        while frontier:
            node = frontier.popleft()
            for child in dag.get(node, []):
                indeg[child] -= 1
                if indeg[child] == 0:
                    next_frontier.append(child)
        frontier = deque(next_frontier)
        max_width = max(max_width, len(frontier))
    return max_width

