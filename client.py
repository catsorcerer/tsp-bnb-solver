import requests
import json
from pydantic import BaseModel
from typing import Union, Optional
import re
import time
import hashlib
import secrets
import string

current_session_token: Optional[str] = None
current_technical_token: Optional[str] = None
current_user_login: Optional[str] = None

class User(BaseModel):
    login: str
    password: str

def send_post(url, data):
    try:
        response = requests.post(url, json=data)
        return response.text, response.status_code
    except requests.exceptions.ConnectionError:
        print("Ошибка соединения")
        return None, 503

def send_signed_request_v5(method: str, url: str, data: Optional[dict] = None):
    global current_session_token
    
    if not current_session_token:
        print("Ошибка: Не выполнен вход в систему")
        return None, 401
    
    request_data = data or {}
    request_body = json.dumps(request_data, sort_keys=True) if method in ['POST', 'PATCH'] else ""
    timestamp = int(time.time())
    
    signature = hashlib.sha256(f"{current_session_token}_{request_body}_{timestamp}".encode()).hexdigest()
    
    headers = {
        'Authorization': f'Bearer {signature}',
        'X-Session-Token': current_session_token,
        'X-Signature-Time': str(timestamp)
    }
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers)
        elif method == 'PATCH':
            response = requests.patch(url, json=data, headers=headers)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
            
        return response.text, response.status_code
    except requests.exceptions.ConnectionError:
        print("Ошибка соединения")
        return None, 503

def validate_password(password):
    if len(password) < 10: return "Пароль должен содержать не менее 10 символов"
    if not re.search(r'[A-Z]', password): return "Пароль должен содержать хотя бы одну заглавную букву"
    if not re.search(r'[a-z]', password): return "Пароль должен содержать хотя бы одну строчную букву"
    if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password): return "Пароль должен содержать хотя бы один спецсимвол"
    return None

def logout():
    global current_session_token, current_technical_token, current_user_login
    if current_user_login: print(f"\nПользователь {current_user_login} вышел из системы")
    else: print("\nВыход из системы")
    current_session_token = None
    current_technical_token = None
    current_user_login = None

def register_user():
    print("\nРЕГИСТРАЦИЯ")
    login = input("Введите логин: ")
    password = input("Введите пароль: ")
    
    password_error = validate_password(password)
    if password_error:
        print(f"Ошибка в пароле: {password_error}")
        return
    
    if password != input("Подтвердите пароль: "):
        print("Ошибка: Пароли не совпадают!")
        return
    
    result, code = send_post("http://localhost:8000/users/", {"login": login, "password": password})
    
    if code == 200:
        try:
            response_data = json.loads(result)
            print("Регистрация успешна!")
            print(f"Ваш технический токен: {response_data.get('token', 'Не получен')}")
        except:
            print("Регистрация успешна! (ответ сервера не разобран)")
    elif code == 400 and result:
        error_data = json.loads(result)
        print(f"Ошибка регистрации: {error_data.get('detail', 'Неизвестная ошибка')}")
    else:
        print(f"Ошибка при регистрации: {code}")

def auth_user():
    global current_session_token, current_technical_token, current_user_login
    
    print("\nАВТОРИЗАЦИЯ")
    login = input("Введите логин: ")
    password = input("Введите пароль: ")
    result, code = send_post("http://localhost:8000/users/auth", {"login": login, "password": password})
    
    if code == 200 and result:
        user_data = json.loads(result)
        current_session_token = user_data['session_token']
        current_technical_token = user_data['token']
        current_user_login = user_data['login']
        
        print(f"Авторизация успешна! Добро пожаловать, {current_user_login}!")
        return True
    elif code == 401:
        print("Ошибка авторизации: Неверный логин или пароль")
        return False
    else:
        print(f"Ошибка при авторизации: {code}")
        return False

def solve_tsp():
    print("\nРЕШЕНИЕ ЗАДАЧИ TSP")
    
    try:
        n = int(input("Количество городов: "))
        if n <= 1:
            print("Ошибка: Количество городов должно быть больше 1")
            return
            
        matrix = []
        for i in range(n):
            row = [float(x.strip()) for x in input(f"Строка {i+1}: ").split(',')]
            if len(row) != n or any(v < 0 for v in row):
                print("Ошибка: Неверное количество чисел или отрицательное расстояние")
                return
            matrix.append(row)
        
        tsp_data = {"matrix": matrix}
        
        result, code = send_signed_request_v5("POST", "http://localhost:8000/solve", tsp_data)
        
        if result is None: return
            
        if code == 200:
            solution = json.loads(result)
            print(f"Оптимальный путь: {solution['path']}")
            print(f"Минимальное расстояние: {solution['distance']}")
        elif code == 401:
            print("Ошибка авторизации: Неверная подпись запроса или сессия истекла")
        elif code == 400:
            error_data = json.loads(result)
            print(f"Ошибка решения TSP: {error_data.get('detail', 'Неизвестная ошибка')}")
        else:
            print(f"Ошибка при решении TSP: {code}")
            
    except ValueError:
        print("Неверный формат данных!")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")

def show_history():
    print("\nИСТОРИЯ ДЕЙСТВИЙ")
    
    result, code = send_signed_request_v5("GET", "http://localhost:8000/users/history")
    
    if result is None: return
        
    if code == 200:
        history_data = json.loads(result)
        print(f"История действий пользователя {history_data['login']}:")
        if not history_data['history']: print("История действий пуста")
            
        for i, entry in enumerate(history_data['history'], 1):
            print(f"{i}. [{entry['timestamp']}] {entry['action']}")
            if entry['details']: print(f"   Детали: {entry['details']}")
    elif code == 401:
        print("Ошибка авторизации: Неверная подпись запроса или сессия истекла")
    else:
        print(f"Ошибка при получении истории: {code}")

def delete_history():
    print("\nУДАЛЕНИЕ ИСТОРИИ")
    
    if input("Вы уверены, что хотите удалить историю действий? (да/нет): ").lower() != 'да':
        print("Удаление отменено.")
        return

    result, code = send_signed_request_v5("DELETE", "http://localhost:8000/users/history")
    
    if result is None: return
        
    if code == 200:
        print("История успешно удалена.")
    elif code == 401:
        print("Ошибка авторизации: Неверная подпись запроса или сессия истекла")
    else:
        print(f"Ошибка при удалении истории: {code}")

def change_password():
    print("\nСМЕНА ПАРОЛЯ")
    
    old_password = input("Введите старый пароль: ")
    new_password = input("Введите новый пароль: ")
    
    password_error = validate_password(new_password)
    if password_error:
        print(f"Ошибка в новом пароле: {password_error}")
        return
    
    if new_password != input("Подтвердите новый пароль: "):
        print("Ошибка: Новые пароли не совпадают!")
        return

    change_data = {"old_password": old_password, "new_password": new_password}
    result, code = send_signed_request_v5("PATCH", "http://localhost:8000/users/password", change_data)

    if result is None: return
        
    if code == 200:
        print("Успех: Пароль и токен обновлены. Вам необходимо выполнить повторный вход.")
        logout()
    elif code == 400:
        error_data = json.loads(result)
        print(f"Ошибка: {error_data.get('detail', 'Неверные данные')}")
    elif code == 401:
        print("Ошибка авторизации: Неверная подпись запроса или сессия истекла")
    else:
        print(f"Ошибка при смене пароля: {code}")

def main_menu():
    while True:
        try:
            if current_session_token:
                print(f"\nОСНОВНОЕ МЕНЮ (Пользователь: {current_user_login})")
                print("1 – Решить задачу TSP")
                print("2 – Показать историю действий")
                print("3 – Удалить историю действий")
                print("4 – Сменить пароль")
                print("5 – Выйти из системы")
                print("0 – Завершить программу")
                
                command = int(input(">>> "))
                match command:
                    case 1: solve_tsp()
                    case 2: show_history()
                    case 3: delete_history()
                    case 4: change_password()
                    case 5: logout()
                    case 0: 
                        print("Выход из программы...")
                        break
                    case _: print("Неизвестная команда")
            else:
                print("\nМЕНЮ ВХОДА")
                print("1 – Регистрация")
                print("2 – Авторизация")
                print("0 – Выход")
                
                command = int(input(">>> "))
                match command:
                    case 1: register_user()
                    case 2: auth_user()
                    case 0:
                        print("Выход из программы...")
                        break
                    case _: print("Неизвестная команда")
        except ValueError:
            print("Неверно введена команда!")
        except KeyboardInterrupt:
            print("\nПрограмма завершена")
            break

if __name__ == "__main__":
    main_menu()
