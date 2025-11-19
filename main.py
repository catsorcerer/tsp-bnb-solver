from fastapi import FastAPI
import math
app = FastAPI()
def reduce_matrix(matrix):
    reduction = 0
    n = len(matrix)
    for i in range(n):
        row = [x for x in matrix[i] if x != math.inf]
        if row:
            min_val = min(row)
            if min_val > 0:
                reduction += min_val
                for j in range(n):
                    if matrix[i][j] != math.inf:
                        matrix[i][j] -= min_val
    for j in range(n):
        col = [matrix[i][j] for i in range(n) if matrix[i][j] != math.inf]
        if col:
            min_val = min(col)
            if min_val > 0:
                reduction += min_val
                for i in range(n):
                    if matrix[i][j] != math.inf:
                        matrix[i][j] -= min_val
    return matrix, reduction
@app.post("/solve")
def solve_tsp(data: dict):
    matrix = data.get("matrix", [])
    n = len(matrix)
    processed = []
    for i in range(n):
        row = []
        for j in range(n):
            if i == j or matrix[i][j] == 0:
                row.append(math.inf)
            else:
                row.append(matrix[i][j])
        processed.append(row)
    best_cost = math.inf  
    best_path = None      
    queue = []            
    start_matrix = [row[:] for row in processed]  
    reduced, bound = reduce_matrix(start_matrix)   
    queue.append((bound, 0, [0], reduced))
    while queue:
        min_idx = 0
        for i in range(1, len(queue)):
            if queue[i][0] < queue[min_idx][0]:
                min_idx = i
        bound, cost, path, node_matrix = queue.pop(min_idx)
        if bound >= best_cost:
            continue
        if len(path) == n:
            total = cost + processed[path[-1]][0]
            if total < best_cost:
                best_cost = total
                best_path = path + [0]  
            continue
        current_city = path[-1]  
        for next_city in range(n):
            if next_city not in path and node_matrix[current_city][next_city] != math.inf:
                new_matrix = [row[:] for row in node_matrix]
                new_cost = cost + processed[current_city][next_city]
                new_path = path + [next_city]
                for city in path:
                    new_matrix[city][next_city] = math.inf  
                    new_matrix[next_city][city] = math.inf  
                reduced, reduction = reduce_matrix(new_matrix)
                new_bound = new_cost + reduction
                if new_bound < best_cost:
                    queue.append((new_bound, new_cost, new_path, reduced))
    return {
        "distance": best_cost if best_cost != math.inf else "No solution",
        "path": best_path
    }