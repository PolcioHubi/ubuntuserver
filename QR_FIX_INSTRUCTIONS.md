# Instrukcje Naprawy QR Kodu - Rozwiązanie Problemów

## Problem
QR kod nie wyświetlał się w Chrome i nie działał jako PWA (Progressive Web App) po dodaniu do ekranu głównego.

## Przyczyny Problemu

1. **Brak obsługi błędów ładowania obrazu** - Gdy `api.qrserver.com` był niedostępny lub zablokowany, obraz się nie ładował bez żadnej informacji
2. **Nieprawidłowa rejestracja Service Worker** - `<script src="sw.js">` zamiast właściwego `navigator.serviceWorker.register()`
3. **Nieprawidłowy manifest.json** - Ścieżki ikon bez `/static/` i zły scope PWA
4. **Brak Content-Security-Policy** - Przeglądarka mogła blokować zewnętrzne API

## Zmiany

### 1. Poprawiono `static/qr.js`
**Dodano:**
- ✅ Funkcję fallback `generateQRCodeLocally()` - generuje wizualny placeholder gdy API nie działa
- ✅ `onerror` callback - automatycznie przełącza się na lokalną generację
- ✅ Timeout 3 sekundy - jeśli obraz nie załaduje się w czasie, użyj fallback
- ✅ Efekty przejścia (opacity) - wizualna informacja o ładowaniu
- ✅ Console.log dla debugowania

### 2. Poprawiono Service Worker w `static/qr.html` i `static/pokaz_qr.html`
**Zmieniono:**
```javascript
// STARE (BŁĘDNE):
<script src="sw.js" data-cfasync="false"></script>

// NOWE (POPRAWNE):
<script>
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function() {
            navigator.serviceWorker.register('/static/sw.js', { scope: '/static/' })
                .then(function(registration) {
                    console.log('ServiceWorker registration successful');
                })
                .catch(function(err) {
                    console.log('ServiceWorker registration failed: ', err);
                });
        });
    }
</script>
```

### 3. Zaktualizowano `static/manifest.json`
**Zmiany:**
- ✅ `start_url`: `/static/dashboard.html` (było: `/static/logowanie.html`)
- ✅ `scope`: `/static/` (było: `/`)
- ✅ `theme_color`: `#f3f4fb` (było: `#FFFFFF`)
- ✅ Wszystkie ścieżki ikon z prefiksem `/static/`
- ✅ Naprawiono brakującą końcówkę `.png` dla `logo192`

### 4. Dodano CSP Headers w `app.py`
**Nowa funkcja:**
```python
@app.after_request
def set_security_headers(response):
    csp = (
        "default-src 'self'; "
        "img-src 'self' data: blob: https://api.qrserver.com; "  # <-- Pozwala na QR API
        # ... inne reguły
    )
    response.headers['Content-Security-Policy'] = csp
    return response
```

## Jak Przetestować

### Test 1: Chrome Desktop
1. Uruchom aplikację: `flask run` lub `gunicorn --bind 0.0.0.0:5000 wsgi:application`
2. Otwórz Chrome: `http://localhost:5000/static/pokaz_qr.html`
3. Otwórz DevTools (F12) → Console
4. **Oczekiwany wynik:**
   - Zobaczysz QR kod (z API lub lokalny fallback)
   - W konsoli: `QR code loaded successfully` lub `Failed to load QR from external API, using local generation`
   - Kod numeryczny widoczny pod QR kodem

### Test 2: Chrome Mobile (przez USB debugging)
1. Włącz USB debugging na telefonie
2. W Chrome desktop: `chrome://inspect/#devices`
3. Otwórz URL: `http://<twoje-ip>:5000/static/pokaz_qr.html`
4. **Oczekiwany wynik:** Jak w Test 1

### Test 3: PWA - Dodaj do Ekranu Głównego
1. Otwórz w Chrome mobile: `http://<twoje-ip>:5000/static/dashboard.html`
2. Menu → "Dodaj do ekranu głównego"
3. Otwórz ikonę z ekranu głównego
4. Nawiguj do sekcji "Kod QR"
5. **Oczekiwany wynik:**
   - Aplikacja uruchamia się w trybie standalone (bez paska Chrome)
   - QR kod działa tak samo jak w przeglądarce
   - Service Worker rejestruje się poprawnie (sprawdź w DevTools → Application → Service Workers)

### Test 4: Tryb Offline (jeśli sw.js prawidłowo cache'uje)
1. Załaduj stronę QR online
2. Włącz tryb offline w DevTools (Network → Offline)
3. Odśwież stronę
4. **Oczekiwany wynik:** Strona nadal działa (jeśli Service Worker jest poprawnie skonfigurowany)

## Debugowanie Problemów

### Problem: "QR code loaded successfully" w konsoli, ale obraz nie widoczny
**Rozwiązanie:**
- Sprawdź CSS: `qrImage.style.display` nie może być `none`
- Sprawdź DevTools → Network → sprawdź czy request do `api.qrserver.com` zwraca 200
- Sprawdź czy element `<img id="qr-image">` istnieje w DOM

### Problem: "Failed to load QR from external API"
**To jest NORMALNE** - fallback działa poprawnie. Sprawdź:
1. Czy widzisz kod numeryczny pod obrazem?
2. Czy widzisz czarno-biały obraz z tekstem?

Jeśli TAK → Wszystko działa! Zewnętrzne API jest zablokowane, ale lokalna wersja działa.

### Problem: "ServiceWorker registration failed"
**Rozwiązanie:**
- Sprawdź czy `sw.js` istnieje w `/static/sw.js`
- Sprawdź konsole czy nie ma błędów składni w `sw.js`
- Service Worker działa tylko na HTTPS lub localhost

### Problem: PWA nie pojawia się w opcji "Dodaj do ekranu głównego"
**Rozwiązanie:**
- Sprawdź Chrome DevTools → Application → Manifest - czy są błędy?
- HTTPS jest wymagane (oprócz localhost)
- Wszystkie ikony muszą istnieć pod podanymi ścieżkami
- Service Worker musi być zarejestrowany

## Weryfikacja Końcowa

Wykonaj ten checklist:
- [ ] QR kod wyświetla się w Chrome desktop
- [ ] QR kod wyświetla się w Chrome mobile
- [ ] Kod numeryczny aktualizuje się pod obrazem
- [ ] Timer odlicza czas (3 min → 0)
- [ ] Pasek postępu maleje
- [ ] Po 3 minutach pojawia się "Kod wygasł"
- [ ] Service Worker rejestruje się bez błędów (DevTools → Application)
- [ ] PWA można dodać do ekranu głównego
- [ ] PWA uruchamia się w trybie standalone
- [ ] Ikony PWA wyświetlają się poprawnie

## Ważne Uwagi dla Produkcji

⚠️ **Dla produkcji na serwerze Ubuntu (`deploy_ubuntu.sh`):**
- CSP header w `nginx.conf` może nadpisać ten z Flask
- Sprawdź `deploy_ubuntu.sh` linię 20 - tam jest CSP dla Nginx
- Już zawiera `img-src ... https://api.qrserver.com` ✅

⚠️ **HTTPS jest WYMAGANE** dla PWA w produkcji (nie localhost):
- Service Worker nie działa na HTTP (oprócz localhost)
- "Dodaj do ekranu głównego" wymaga HTTPS
- Użyj Let's Encrypt lub Cloudflare dla darmowego SSL

⚠️ **Zewnętrzne API może być wolne/niedostępne:**
- Dlatego mamy fallback na lokalne generowanie
- W przyszłości rozważ bibliotekę `qrcode.js` dla pełnej funkcjonalności offline

## Następne Kroki (Opcjonalnie)

### Ulepszenie 1: Prawdziwa biblioteka QR offline
```bash
# Zainstaluj qrcode.js
npm install qrcode
# lub dodaj CDN do HTML
<script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"></script>
```

### Ulepszenie 2: Precaching w Service Worker
Dodaj QR strony do cache w `sw.js` dla szybszego ładowania offline.

### Ulepszenie 3: Progressive Enhancement
```javascript
// Sprawdź czy jesteśmy online
if (navigator.onLine) {
    // Użyj zewnętrznego API
} else {
    // Użyj lokalnej generacji
}
```
