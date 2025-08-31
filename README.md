# ImageWrangler

Aplikacja do wsadowego przetwarzania obrazów z graficznym interfejsem użytkownika w PySide6.

## Funkcje

- **Zmiana rozmiaru obrazów**: Zmiana rozmiaru wielu obrazów jednocześnie z możliwością ustawienia szerokości i wysokości docelowej
- **Inwersja kolorów**: Inwersja kolorów wybranych obrazów
- **Obsługa formatów**: JPEG, PNG, WEBP, BMP, TIFF, HEIC, HEIF
- **Wybór formatu wyjściowego**: JPEG, PNG, WEBP

## Instalacja

1. Zainstaluj wymagane biblioteki:
```bash
pip install -r requirements.txt
```

2. Uruchom aplikację:
```bash
python main.py
```

## Użytkowanie

1. **Wybierz obrazy**: Kliknij "Select Images" i wybierz pliki obrazów do przetworzenia
2. **Wybierz katalog wyjściowy**: Kliknij "Select Output Directory" i wybierz folder, w którym mają być zapisane przetworzone obrazy
3. **Wybierz operację**:
   - **Resize Images**: Ustaw docelową szerokość, wysokość i format, następnie kliknij "Resize Images"
   - **Invert Colors**: Wybierz format wyjściowy i kliknij "Invert Colors"
4. **Obserwuj postęp**: Pasek postępu i status pokażą postęp przetwarzania

## Wymagania systemowe

- Python 3.7+
- PySide6
- Pillow
- pillow-heif (dla obsługi HEIC/HEIF)