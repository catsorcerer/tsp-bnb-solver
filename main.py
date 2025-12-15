from typing import Union, Optional
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import json
import time
import os
import random
import math
import hashlib
import secrets
import string
from datetime import datetime
import re

app = FastAPI()

LOGS_DIR = 'user_logs/'
USERS_DIR = 'users/'

class User(BaseModel):
    login: str
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
    session_token: str

class TSPRequest(BaseModel):
    matrix: list[list[float]]

class TSPResponse(BaseModel):
    distance: Union[float, str]
    path: Union[list[int], None]

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

session_tokens = {}

def validate_password(password):
    if len(password) < 10:
        return "Пароль должен содержать не менее 10 символов"
    if not re.search(r'[A-Z]', password):
        return "Пароль должен содержать хотя бы одну заглавную букву"
    if not re.search(r'[a-z]', password):
        return "Пароль должен содержать хотя бы одну строчную букву"
    if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
        return "Пароль должен содержать хотя бы один спецсимвол"
    return None

def get_user_file_path(user: User) -> str:
    return os.path.join(USERS_DIR, f"user_{user.id}.json")

def save_user(user: User):
    if not os.path.exists(USERS_DIR):
        os.makedirs(USERS_DIR)
    with open(get_user_file_path(user), 'w') as f:
        json.dump(user.model_dump(), f)

def get_user_log_path(login: str) -> str:
    return os.path.join(LOGS_DIR, f"{login}_history.json")

def load_user_history(login: str) -> list:
    log_path = get_user_log_path(login)
    if not os.path.exists(log_path): return []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_user_history(login: str, history: list):
    if not os.path.exists(LOGS_DIR): os.makedirs(LOGS_DIR)
    log_path = get_user_log_path(login)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

def add_user_history(user_login: str, action: str, details: str = ""):
    history = load_user_history(user_login)
    history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "details": details
    })
    if len(history) > 50: history = history[-50:]
    save_user_history(user_login, history)

def is_login_taken(login:str) -> bool:
    if not os.path.exists(USERS_DIR): return False
    for file in os.listdir(USERS_DIR):
        if file.endswith('.json'):
            with open(f"{USERS_DIR}/{file}", 'r') as f:
                user_data = json.load(f)
                if user_data.get('login') == login:
                    return True
    return False

def get_user_by_token(token: str) -> Optional[User]:
    if not os.path.exists(USERS_DIR): return None
    for file in os.listdir(USERS_DIR):
        if file.endswith('.json'):
            with open(f"{USERS_DIR}/{file}", 'r') as f:
                user_data = json.load(f)
                if user_data.get('token') == token:
                    return User(**user_data)
    return None

def verify_signature(authorization: Optional[str], x_session_token: Optional[str], x_signature_time: Optional[str], request_body: str, time_window: int = 300) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "): return None
    if not x_session_token: return None
    if not x_signature_time: return None
        
    try:
        received_time = int(x_signature_time)
    except ValueError:
        return None

    received_hash = authorization[7:]
    current_time = int(time.time())
    
    if abs(current_time - received_time) > time_window: return None
    if x_session_token not in session_tokens: return None
    
    technical_token = session_tokens[x_session_token]
    expected_hash = hashlib.sha256(f"{x_session_token}_{request_body}_{received_time}".encode()).hexdigest()
    
    if received_hash == expected_hash:
        return get_user_by_token(technical_token)
    return None

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
    
    if any(len(row) != n for row in matrix):
        raise ValueError("Матрица должна быть квадратной (N x N)")
        
    processed = []
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
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
                
                for i in range(n):
                    new_matrix[current_city][i] = math.inf
                    new_matrix[i][next_city] = math.inf
                new_matrix[next_city][current_city] = math.inf

                new_cost = cost + processed[current_city][next_city]
                new_path = path + [next_city]
                
                reduced, reduction = reduce_matrix(new_matrix)
                new_bound = new_cost + reduction
                
                if new_bound < best_cost:
                    queue.append((new_bound, new_cost, new_path, reduced))
                    
    return {
        "distance": best_cost if best_cost != math.inf else "No solution",
        "path": best_path
    }

@app.post("/users/")
def create_user(user: User):
    if is_login_taken(user.login):
        raise HTTPException(status_code=400, detail="Логин уже занят")
        
    user.id = int(time.time() * 1000)
    user.token = str(secrets.token_hex(32))
    
    save_user(user)
    add_user_history(user.login, "Регистрация", f"Пользователь {user.login} зарегистрирован")
    
    return {"login": user.login, "token": user.token, "role": user.role}

@app.post("/users/auth")
def auth_user(params: AuthUser):
    json_files_names = [file for file in os.listdir(USERS_DIR) if file.endswith('.json')]
    for json_file_name in json_files_names:
        file_path = os.path.join(USERS_DIR, json_file_name)
        with open(file_path, 'r') as f:
            user = User(**json.load(f))
        
        if user.login == params.login and user.password == params.password:
            session_token = hashlib.sha256(f"{user.token}_{secrets.token_hex(32)}_{time.time()}".encode()).hexdigest()
            session_tokens[session_token] = user.token 
            
            add_user_history(user.login, "Авторизация", "Успешный вход в систему")
            
            return AuthResponse(
                login=user.login,
                token=user.token,
                session_token=session_token
            )
    raise HTTPException(status_code=401, detail="Invalid login or password")

@app.get("/users/history")
def get_user_history(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    x_signature_time: Optional[str] = Header(None)
):
    request_body = ""
    user = verify_signature(authorization, x_session_token, x_signature_time, request_body) 
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session signature")
    
    return {"login": user.login, "history": load_user_history(user.login)}

@app.delete("/users/history")
def delete_user_history(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    x_signature_time: Optional[str] = Header(None)
):
    request_body = ""
    user = verify_signature(authorization, x_session_token, x_signature_time, request_body) 
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session signature")
    
    log_path = get_user_log_path(user.login)
    if os.path.exists(log_path): os.remove(log_path)
    
    add_user_history(user.login, "Удаление истории", "История действий пользователя очищена")
    
    return {"message": "User history deleted successfully"}


@app.patch("/users/password")
def change_user_password(
    password_request: ChangePasswordRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    x_signature_time: Optional[str] = Header(None)
):
    request_body = json.dumps(password_request.model_dump(), sort_keys=True)
    user = verify_signature(authorization, x_session_token, x_signature_time, request_body)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session signature")
    
    if user.password != password_request.old_password:
        raise HTTPException(status_code=400, detail="Неверный старый пароль")

    password_error = validate_password(password_request.new_password)
    if password_error:
        raise HTTPException(status_code=400, detail=password_error)
        
    old_token = user.token
    user.password = password_request.new_password
    user.token = str(secrets.token_hex(32))
    save_user(user)
    
    session_tokens_to_remove = [k for k, v in session_tokens.items() if v == old_token]
    for token_to_remove in session_tokens_to_remove:
        del session_tokens[token_to_remove]

    add_user_history(user.login, "Изменение пароля и токена", "Пароль и технический токен обновлены. Требуется повторный вход.")
    
    return {"message": "Пароль и технический токен успешно обновлены. Требуется повторный вход (реавторизация)."}

@app.post("/solve", response_model=TSPResponse)
def solve_tsp(
    tsp_request: TSPRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    x_signature_time: Optional[str] = Header(None)
):
    request_body = json.dumps(tsp_request.model_dump(), sort_keys=True)
    user = verify_signature(authorization, x_session_token, x_signature_time, request_body)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session signature")
    
    try:
        matrix = tsp_request.matrix
        n = len(matrix)
        if n < 2 or any(len(row) != n for row in matrix) or any(val < 0 for row in matrix for val in row):
            raise HTTPException(status_code=400, detail="Неверный формат матрицы или отрицательные расстояния")
        
        result = solve_tsp_internal(tsp_request.matrix)
        add_user_history(user.login, "Решение TSP", f"Матрица {n}x{n}, результат: {result['distance']}")
        
        return TSPResponse(distance=result["distance"], path=result["path"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error solving TSP: {str(e)}")
