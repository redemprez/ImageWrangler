#!/usr/bin/env python3
"""
Skrypt do budowania pliku exe dla ImageWrangler
"""

import PyInstaller.__main__
import os
import sys

def build_exe():
    """Buduje plik exe za pomocą PyInstaller"""
    
    # Parametry dla PyInstaller
    pyinstaller_args = [
        'main.py',
        '--onefile',                    # Jeden plik exe
        '--windowed',                   # Bez konsoli (GUI aplikacja)
        '--name=ImageWrangler',         # Nazwa pliku exe
        '--distpath=dist',              # Folder docelowy
        '--workpath=build',             # Folder roboczy
        '--specpath=.',                 # Gdzie zapisać plik .spec
        '--clean',                      # Wyczyść cache przed budowaniem
        '--noconfirm',                  # Nie pytaj o potwierdzenie
        '--add-data=requirements.txt;.', # Dodaj requirements.txt
    ]
    
    print("Budowanie ImageWrangler.exe...")
    print("To może zająć kilka minut...")
    
    # Uruchom PyInstaller
    PyInstaller.__main__.run(pyinstaller_args)
    
    print("\nBudowanie zakończone!")
    print("Plik ImageWrangler.exe znajduje się w folderze 'dist'")

if __name__ == "__main__":
    build_exe()