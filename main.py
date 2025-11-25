from typing import Union
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import json
import time
import os
import random
import math
from typing import Optional

app = FastAPI()

class User(BaseModel):
    login: str
    email: str
    password: str
    role: Union[str, None] = "basic role"
    token: Union[str, None] = None
    id: Union[int, None] = -1

class AuthUser(BaseModel):
    login: str
    password: str

class AuthResponse(BaseModel):
    login: str
    token: str

class TSPRequest(BaseModel):
    matrix: list[list[float]]

class TSPResponse(BaseModel):
    distance: Union[float, str]
    path: Union[list[int], None]

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

def solve_tsp_internal(matrix):
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

def is_login_taken(login:str) -> bool:
    if not os.path.exists('users/'):
        return False

    for file in os.listdir('users/'):
        if file.endswith('.json'):
            with open(f"users/{file}", 'r') as f:
                user_data = json.load(f)
                if user_data.get('login') == login:
                    return True
    return False

def get_user_by_token(token: str) -> Optional[User]:
    """Поиск пользователя по токену"""
    if not os.path.exists('users/'):
        return None
    
    for file in os.listdir('users/'):
        if file.endswith('.json'):
            with open(f"users/{file}", 'r') as f:
                user_data = json.load(f)
                if user_data.get('token') == token:
                    return User(**user_data)
    return None

def verify_signature_v1(authorization: Optional[str]) -> Optional[User]:
    """Вариант 1: Простая проверка токена"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization[7:]  
    return get_user_by_token(token)

@app.get("/")
def root_path():
    return {"TSP Solver"}

@app.post("/users/")
def create_user(user: User):
    
    if is_login_taken(user.login):
        raise HTTPException(status_code=400, detail="Логин уже занят")
        
    user.id = int(time.time())
    user.token = str(random.getrandbits(128))
    with open(f"users/user_{user.id}.json", 'w') as f:
        json.dump(user.model_dump(), f)
    return user

@app.post("/users/auth")
def auth_user(params: AuthUser):
    json_files_names = [file for file in os.listdir('users/') if file.endswith('.json')]
    for json_file_name in json_files_names:
        file_path = os.path.join('users/', json_file_name)
        with open(file_path, 'r') as f:
            json_item = json.load(f)
        user = User(**json_item)
        if user.login == params.login and user.password == params.password:
            return AuthResponse(login=user.login, token=user.token)
    raise HTTPException(status_code=401, detail="Invalid login or password")

@app.post("/solve", response_model=TSPResponse)
def solve_tsp(
    tsp_request: TSPRequest,
    authorization: Optional[str] = Header(None)
):
    user = verify_signature_v1(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        matrix = tsp_request.matrix
        n = len(matrix)

        if n < 2:
            raise HTTPException(status_code=400, detail="Матрица должна содержать минимум 2 города")
        
        for i in range(n):
            for j in range(n):
                if matrix[i][j] < 0:
                    raise HTTPException(status_code=400, detail="Расстояния не могут быть отрицательными")
        
        result = solve_tsp_internal(tsp_request.matrix)
        return TSPResponse(
            distance=result["distance"],
            path=result["path"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error solving TSP: {str(e)}")
