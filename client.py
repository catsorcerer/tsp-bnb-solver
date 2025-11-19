import requests
import json

def send_post(url, data):
    response = requests.post(url, json=data)
    return response.text, response.status_code

def solve_tsp():
    print("\n--- Решение задачи коммивояжера ---")
    print("Введите матрицу расстояний:")
    
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
            matrix.append(row)
        
        tsp_data = {"matrix": matrix}
        result, code = send_post("http://localhost:8000/solve", tsp_data)
        
        if code == 200:
            solution = json.loads(result)
            print(f"Оптимальный путь: {solution['path']}")
            print(f"Минимальное расстояние: {solution['distance']}")
        else:
            print(f"Ошибка при решении TSP: {code}")
            
    except ValueError:
        print("Неверный формат данных!")
    except Exception as e:
        print(f"Ошибка: {e}")

while True:
    try:
        print("\n" + "="*40)
        command = int(input("1 – решить TSP\n0 – выход\n>>> "))
        if command == 1:
            solve_tsp()
        elif command == 0:
            print("Выход из программы...")
            break
        else:
            print("Неизвестная команда")
    except ValueError:
        print("Неверно введена команда!")
