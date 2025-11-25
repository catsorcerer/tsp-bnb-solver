import requests
import json
from pydantic import BaseModel
from typing import Union
import re

class User(BaseModel):
    login: str
    email: str
    password: str
    role: Union[str, None] = "basic role"
    token: Union[str, None] = None
    id: Union[int, None] = -1

def send_post(url, data):
    response = requests.post(url, json=data)
    return response.text, response.status_code

def send_signed_post_v1(url, data, token):
    """Отправка запроса с подписью Вариант 1: простой токен"""
    headers = {
        'Authorization': f'Bearer {token}'
    }
    response = requests.post(url, json=data, headers=headers)
    return response.text, response.status_code

def validate_password(password):
    """Проверка сложности пароля"""
    if len(password) < 10:
        return "Пароль должен содержать не менее 10 символов"
    if not re.search(r'[A-Z]', password):
        return "Пароль должен содержать хотя бы одну заглавную букву"
    if not re.search(r'[a-z]', password):
        return "Пароль должен содержать хотя бы одну строчную букву"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return "Пароль должен содержать хотя бы один спецсимвол"
    return None

def register_user():
    login = input("Введите логин: ")
    email = input("Введите email: ")
    password = input("Введите пароль: ")
    
    password_error = validate_password(password)
    if password_error:
        print(f"Ошибка в пароле: {password_error}")
        return
    
    password_confirm = input("Подтвердите пароль: ")
    if password != password_confirm:
        print("Ошибка: Пароли не совпадают!")
        return
    
    user_data = {
        "login": login,
        "email": email,
        "password": password
    }
    result, code = send_post("http://localhost:8000/users/", user_data)
    
    if code == 200:
        print("Регистрация успешна!")
    elif code == 400:

        try:
            error_data = json.loads(result)
            print(f"Ошибка регистрации: {error_data.get('detail', 'Неизвестная ошибка')}")
        except:
            print("Ошибка регистрации: Логин уже занят или неверные данные")
    else:
        print(f"Ошибка при регистрации: {code}")

def auth_user():
    login = input("Введите логин: ")
    password = input("Введите пароль: ")
    auth_data = {
        "login": login,
        "password": password
    }
    result, code = send_post("http://localhost:8000/users/auth", auth_data)
    
    if code == 200:
        user_data = json.loads(result)
        print("Авторизация успешна!")
        print(f"Ваш токен: {user_data['token']}")
        return user_data['token']
    elif code == 401:
        print("Ошибка авторизации: Неверный логин или пароль")
        return None
    else:
        print(f"Ошибка при авторизации: {code}")
        return None

def solve_tsp():
    print("Введите матрицу расстояний:")
    
    # Сначала получаем токен через авторизацию
    token = auth_user()
    if not token:
        return
    
    try:
        n = int(input("Количество городов: "))
        matrix = []
        
        print(f"Введите {n} строк по {n} чисел через запятую:")
        for i in range(n):
            row_input = input(f"Строка {i+1}: ")
            row = [float(x.strip()) for x in row_input.split(',')]
            if len(row) != n:
                print(f"Ошибка: должно быть {n} чисел в строке")
                return

            for value in row:
                if value < 0:
                    print("Ошибка: Расстояния не могут быть отрицательными")
                    return
            matrix.append(row)
        
        tsp_data = {"matrix": matrix}
        
        # Отправляем подписанный запрос (Вариант 1)
        result, code = send_signed_post_v1("http://localhost:8000/solve", tsp_data, token)
        
        if code == 200:
            solution = json.loads(result)
            print(f"Оптимальный путь: {solution['path']}")
            print(f"Минимальное расстояние: {solution['distance']}")
        elif code == 400:
            try:
                error_data = json.loads(result)
                print(f"Ошибка решения TSP: {error_data.get('detail', 'Неизвестная ошибка')}")
            except:
                print("Ошибка решения TSP: Неверные данные")
        elif code == 401:
            print("Ошибка авторизации: Неверный токен")
        else:
            print(f"Ошибка при решении TSP: {code}")
            
    except ValueError:
        print("Неверный формат данных!")
    except Exception as e:
        print(f"Ошибка: {e}")

while True:
    try:
        print("Введите команду:")
        command = int(input("1 – регистрация\n2 – авторизация\n3 – решить TSP\n0 – выход\n>>> "))
        match command:
            case 1:
                register_user()
            case 2:
                auth_user()
            case 3:
                solve_tsp()
            case 0:
                print("Выход из программы...")
                break
            case _:
                print("Неизвестная команда")
    except ValueError:
        print("Неверно введена команда!")
