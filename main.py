import speech_recognition as sr
import pyttsx3
import tkinter as tk
from tkinter import scrolledtext
from openai import OpenAI
import os
from dotenv import load_dotenv
import requests
import datetime
import re

# Cargar las variables de entorno desde el archivo .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
trello_key = os.getenv("TRELLO_KEY")
trello_token = os.getenv("TRELLO_TOKEN")
board_id = os.getenv("TRELLO_BOARD_ID")

# Verificar que las claves API se cargaron correctamente
if not api_key:
    raise ValueError("La clave API de OpenAI no se encuentra en el archivo .env.")
if not trello_key or not trello_token:
    raise ValueError("Las claves de Trello no se encuentran en el archivo .env.")
if not board_id:
    raise ValueError("El ID del tablero de Trello no se encuentra en el archivo .env.")

# Crear una instancia del cliente OpenAI
client = OpenAI(api_key=api_key)

# Configurar el motor de síntesis de voz
engine = pyttsx3.init()

# Función para que el asistente responda
def speak(text):
    engine.say(text)
    engine.runAndWait()

# Función para escuchar al usuario y reconocer el comando
def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Escuchando...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        print("Procesando...")
        command = recognizer.recognize_google(audio, language="es-ES")
        print(f"Usuario dijo: {command}")
        return command.lower()
    except sr.UnknownValueError:
        print("No se pudo entender el audio")
    except sr.RequestError as e:
        print(f"Error en la solicitud: {e}")

    return ""

# Función para generar respuesta utilizando la API actualizada de ChatGPT
def generate_response(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente útil."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error al generar respuesta: {e}")
        return "Lo siento, ocurrió un error al generar la respuesta."

# Lista de tareas
tasks = []
completed_tasks = []

# Función para agregar una tarea
def add_task(task):
    tasks.append(task)
    return add_trello_task(task)

# Función para listar tareas
def list_tasks():
    if tasks:
        return "\n".join(tasks)
    else:
        return "No hay tareas."

# Función para eliminar una tarea
def remove_task(task):
    if task in tasks:
        tasks.remove(task)
        return f"Tarea '{task}' eliminada."
    else:
        return f"Tarea '{task}' no encontrada."

# Función para completar una tarea
def complete_task(task):
    if task in tasks:
        tasks.remove(task)
        completed_tasks.append((task, datetime.datetime.now()))
        return f"Tarea '{task}' completada."
    else:
        return f"Tarea '{task}' no encontrada."

# Función para analizar productividad
def analyze_productivity():
    if not completed_tasks:
        return "No hay datos suficientes para análisis."
    
    times = [t[1].time() for t in completed_tasks]
    avg_hour = sum(t.hour for t in times) / len(times)
    return f"Tu hora promedio de mayor productividad es alrededor de las {int(avg_hour)}:00."

# Función para procesar comandos de voz específicos
def process_command(command):
    command = command.lower()
    
    # Expresión regular para detectar hora en formato "a las [hora]"
    match = re.search(r"a las (\d{1,2})(?::(\d{2}))?\s*(am|pm)?", command)
    time_str = ""
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3)
        if period:
            if period.lower() == 'pm' and hour != 12:
                hour += 12
            elif period.lower() == 'am' and hour == 12:
                hour = 0
        time_str = f" a las {hour:02}:{minute:02}"

    if "agregar tarea" in command:
        task = command.replace("agregar tarea", "").strip()
        return add_task(task + time_str)
    elif "listar tareas" in command:
        return list_tasks()
    elif "eliminar tarea" in command:
        task = command.replace("eliminar tarea", "").strip()
        return remove_task(task)
    elif "completar tarea" in command:
        task = command.replace("completar tarea", "").strip()
        return complete_task(task)
    elif "análisis de productividad" in command:
        return analyze_productivity()
    else:
        return generate_response(command)

# Integración con Trello
def add_trello_task(task):
    list_id = lists_dict.get(list_dropdown_var.get())
    if not list_id:
        return "No se seleccionó una lista para agregar la tarea."

    url = "https://api.trello.com/1/cards"
    query = {
        'key': trello_key,
        'token': trello_token,
        'idList': list_id,
        'name': task
    }
    response = requests.post(url, params=query)
    if response.status_code == 200:
        return f"Tarea '{task}' agregada a Trello en la lista '{list_dropdown_var.get()}'."
    else:
        return f"Error al agregar tarea a Trello: {response.text}"

# Función para obtener listas del tablero
def get_board_lists():
    url = f"https://api.trello.com/1/boards/{board_id}/lists"
    query = {
        'key': trello_key,
        'token': trello_token
    }
    response = requests.get(url, params=query)
    if response.status_code == 200:
        lists = response.json()
        return {lst['name']: lst['id'] for lst in lists}
    else:
        print("Error al obtener las listas del tablero de Trello:", response.text)
        return {}

# Crear GUI mejorada
def create_gui():
    # Ventana principal
    window = tk.Tk()
    window.title("Asistente Personal con ChatGPT y Tareas")
    window.geometry("800x600")

    # Crear elementos de la interfaz
    global entry, text_area, task_list, list_dropdown_var, lists_dict
    label = tk.Label(window, text="Ingresa tu comando o tarea:")
    label.pack(pady=10)

    entry = tk.Entry(window, width=50)
    entry.pack(pady=5)

    button = tk.Button(window, text="Enviar", command=handle_interaction)
    button.pack(pady=10)

    text_area = scrolledtext.ScrolledText(window, width=60, height=20)
    text_area.pack(padx=10, pady=10)

    # Lista de tareas
    task_list_label = tk.Label(window, text="Lista de Tareas:")
    task_list_label.pack(pady=10)

    task_list = tk.Listbox(window, width=60, height=10)
    task_list.pack(padx=10, pady=10)

    # Lista desplegable para seleccionar la lista
    list_label = tk.Label(window, text="Selecciona una lista:")
    list_label.pack(pady=10)

    lists_dict = get_board_lists()
    list_names = list(lists_dict.keys())
    list_dropdown_var = tk.StringVar(window)
    if list_names:
        list_dropdown_var.set(list_names[0])  # Establecer el valor inicial de la lista desplegable
    list_dropdown = tk.OptionMenu(window, list_dropdown_var, *list_names)
    list_dropdown.pack(pady=5)

    window.mainloop()

# Manejo de la interacción con la GUI
def handle_interaction():
    command = entry.get()
    response = process_command(command)
    text_area.insert(tk.END, f"Usuario: {command}\n")
    text_area.insert(tk.END, f"Respuesta: {response}\n")
    entry.delete(0, tk.END)

# Ejecutar la GUI
if __name__ == "__main__":
    create_gui()
