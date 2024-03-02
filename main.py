import pytesseract
import pyautogui
import cv2
import numpy as np
from PIL import ImageGrab
import os
import json
from datetime import datetime
import time
import difflib
import csv
import threading
import keyboard
import pymsgbox

# Configuration de pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Dossier pour stocker les captures
captures_dir = "captures"
if not os.path.exists(captures_dir):
    os.makedirs(captures_dir)

# Fichier de commandes JSON
commands_file = "commands.json"

# Chemin du fichier pour stocker les éléments détectés
elements_file = "elements.csv"

# Variable globale pour contrôler le thread de rafraîchissement
refresh_thread_active = True

#Variable stop
program_running = True

def read_commands_from_json():
    with open(commands_file, 'r', encoding='utf-8') as file:
        return json.load(file)

def capture_and_save_screen():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(captures_dir, f"capture_{timestamp}.png")
    screen = np.array(ImageGrab.grab())
    cv2.imwrite(filename, cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY))
    manage_captures()

def manage_captures():
    captures = [os.path.join(captures_dir, f) for f in os.listdir(captures_dir)]
    captures.sort(key=os.path.getmtime, reverse=True)
    while len(captures) > 10:
        os.remove(captures.pop())

def detect_and_update_elements():
    img = np.array(ImageGrab.grab())
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    data = pytesseract.image_to_data(img_gray, output_type=pytesseract.Output.DICT)
    elements = [word for word in data['text'] if word.strip()]
    
    with open(elements_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Elements"])
        for element in elements:
            writer.writerow([element])

def perform_action(x, y, action):
    actions = read_commands_from_json()
    command_function = actions.get(action)
    if command_function and hasattr(pyautogui, command_function):
        getattr(pyautogui, command_function)(x, y)
    else:
        print(f"Commande invalide : {action}")

def find_and_perform_action(element_name, action_keyword):
    elements = []
    with open(elements_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            elements.extend(row)
    
    match = difflib.get_close_matches(element_name, elements, n=1, cutoff=0.6)
    if match:
        img = np.array(ImageGrab.grab())
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        preprocessed_img = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        data = pytesseract.image_to_data(preprocessed_img, output_type=pytesseract.Output.DICT)
        
        for i, word in enumerate(data['text']):
            if match[0].lower() == word.lower():
                x, y = data['left'][i] + data['width'][i] // 2, data['top'][i] + data['height'][i] // 2
                perform_action(x, y, action_keyword)
                return True

    print(f"Élément '{element_name}' non trouvé.")
    return False

def refresh_loop():
    global refresh_thread_active
    while refresh_thread_active == True:
        capture_and_save_screen()
        detect_and_update_elements()
        print("Éléments et captures d'écran actualisés.")
        time.sleep(5)

# Fonction pour afficher la barre de prompt
def show_prompt_bar():
    global refresh_thread_active, program_running
    threading.Thread(target=refresh_loop, daemon=True).start()
    refresh_thread_active = True
    response = pymsgbox.prompt('Entrez votre commande:', 'Barre de prompt')
    if response != None and response != "exit":
        action_keyword, element_name = response.split(' ', 1)
        print(f"Tentative de trouver et {action_keyword} l'élément '{element_name}'...")
        find_and_perform_action(element_name, action_keyword)
        # Stopper le thread pour actualiser les captures
        refresh_thread_active = False
    
    if response == "exit" or response == None:
        print("Fermeture du programme...")
        refresh_thread_active = False
        #Supprimer tout le texte dans les elements détectés
        with open(elements_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Elements"])
        for file in os.listdir(captures_dir):
            os.remove(os.path.join(captures_dir, file))
        #program_running = False
        refresh_thread_active = False

def main():
    global program_running
    while program_running:
        user_input = input("Entrez votre commande (ou 'exit' pour quitter) : ")
        if user_input.lower() == 'exit':
            #Supprimer tout le texte dans les elements détectés
            with open(elements_file, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Elements"])
            for file in os.listdir(captures_dir):
                os.remove(os.path.join(captures_dir, file))
            
            program_running = False
            break
        
        action_keyword, element_name = user_input.split(' ', 1)
        print(f"Tentative de trouver et {action_keyword} l'élément '{element_name}'...")
        find_and_perform_action(element_name, action_keyword)

# Liaison du raccourci clavier pour afficher la barre de prompt
keyboard.add_hotkey('ctrl+shift+p', show_prompt_bar)

if __name__ == '__main__':
    main()
