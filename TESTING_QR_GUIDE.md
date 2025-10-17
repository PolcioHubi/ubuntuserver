# ⚠️ WAŻNE: Jak Przetestować QR Kody

## Problem: CORS Error przy otwieraniu `file://`

**BŁĄD:**
```
Access to internal resource at 'file:///C:/Users/.../manifest.json' 
from origin 'null' has been blocked by CORS policy
```

**PRZYCZYNA:**
- Otwierasz pliki HTML bezpośrednio z dysku (protokół `file://`)
- Manifest.json, Service Worker i zewnętrzne API **NIE DZIAŁAJĄ** bez serwera HTTP

**ROZWIĄZANIE:**
Zawsze używaj serwera Flask do testowania!

---

## ✅ POPRAWNE Metody Testowania

### Metoda 1: Flask Development Server (ZALECANA)
```bash
# W katalogu projektu
flask run

# Otwórz przeglądarkę:
http://localhost:5000/static/test_qr.html
http://localhost:5000/static/pokaz_qr.html
```

### Metoda 2: Gunicorn (Symulacja Produkcji)
```bash
gunicorn --workers 3 --bind 0.0.0.0:5000 wsgi:application

# Otwórz przeglądarkę:
http://localhost:5000/static/pokaz_qr.html
```

### Metoda 3: Python Simple HTTP Server (Tylko dla statycznych plików)
```bash
cd static
python -m http.server 8000

# Otwórz przeglądarkę:
http://localhost:8000/pokaz_qr.html
```
⚠️ **UWAGA:** Ta metoda NIE uruchamia backendu Flask, więc endpointy API nie będą działać!

---

## Problem: CSP Blokuje `api.qrserver.com`

**BŁĄD:**
```
Refused to connect to 'https://api.qrserver.com/...' 
because it violates the following Content Security Policy directive: 
"connect-src 'self'"
```

**PRZYCZYNA:**
Service Worker używa Fetch API, który wymaga `connect-src` w CSP

**ROZWIĄZANIE:**
✅ Już naprawione! Zaktualizowano:
1. `app.py` - dodano `https://api.qrserver.com` do `connect-src`
2. `deploy_ubuntu.sh` - dodano `https://api.qrserver.com` do `connect-src`

---

## Kompletny Test Workflow

### Krok 1: Uruchom Serwer
```bash
# Terminal 1 - Redis (jeśli nie działa)
redis-server

# Terminal 2 - Flask App
flask run
```

### Krok 2: Sprawdź Console Devtools
1. Otwórz Chrome DevTools (F12)
2. Zakładka **Console** - sprawdź logi:
   - ✅ `ServiceWorker registered successfully`
   - ✅ `QR code loaded successfully` LUB
   - ⚠️ `Failed to load QR from external API, using local generation` (to też OK!)

3. Zakładka **Network** - sprawdź requesty:
   - `api.qrserver.com` - status 200 (lub failed ale lokalny fallback działa)
   - `manifest.json` - status 200
   - `sw.js` - status 200

4. Zakładka **Application**:
   - Service Workers → powinien być zarejestrowany
   - Manifest → sprawdź czy JSON jest poprawny

### Krok 3: Test PWA na Telefonie
```bash
# Znajdź swoje IP
ipconfig  # Windows
ifconfig  # Linux/Mac

# Uruchom Flask na wszystkich interfejsach
flask run --host=0.0.0.0

# Na telefonie otwórz:
http://<TWOJE_IP>:5000/static/dashboard.html

# Menu Chrome → "Dodaj do ekranu głównego"
```

---

## Checklist Debugowania

Jeśli QR nie działa, sprawdź:

### 1. Czy używasz serwera HTTP?
```
❌ file:///C:/Users/kubio/Desktop/...
✅ http://localhost:5000/static/...
```

### 2. Czy Service Worker jest zarejestrowany?
**DevTools → Application → Service Workers**
- Powinien pokazać: `http://localhost:5000/static/sw.js`
- Status: **Activated and running**

### 3. Czy CSP pozwala na QR API?
**DevTools → Network → kliknij na request → Headers**
Sprawdź `Content-Security-Policy`:
```
connect-src 'self' https://api.qrserver.com
img-src 'self' data: blob: https://api.qrserver.com
```

### 4. Czy element QR istnieje w DOM?
**DevTools → Elements → Ctrl+F → szukaj: `qr-image`**
```html
<img id="qr-image" src="..." alt="QR Code">
```

### 5. Czy JavaScript się ładuje?
**DevTools → Sources → static/qr.js**
- Sprawdź czy plik istnieje
- Ustaw breakpoint na linii `updateQRCode()`
- Odśwież stronę - powinien się zatrzymać

---

## Produkcja: Deploy na Ubuntu

Po deploymencie na serwer:

```bash
# SSH do serwera
ssh user@185-167-99-62.cloud-xip.com

# Uruchom deploy script
cd /var/www/mobywatel  # lub gdzie masz projekt
sudo bash deploy_ubuntu.sh

# Sprawdź logi
sudo journalctl -u mobywatel -f
tail -f logs/app.log

# Test z przeglądarki
https://185-167-99-62.cloud-xip.com/static/pokaz_qr.html
```

### Weryfikacja CSP na Produkcji
```bash
# Sprawdź nagłówki Nginx
curl -I https://185-167-99-62.cloud-xip.com/static/pokaz_qr.html | grep -i content-security

# Powinno pokazać:
# content-security-policy: ... connect-src 'self' https://api.qrserver.com ...
```

---

## Najczęstsze Błędy i Rozwiązania

### Błąd: "Mixed Content" na HTTPS
**Problem:** Strona HTTPS próbuje załadować HTTP resource
**Rozwiązanie:** Wszystkie linki muszą być HTTPS (api.qrserver.com jest HTTPS ✅)

### Błąd: "net::ERR_BLOCKED_BY_CLIENT"
**Problem:** AdBlock/uBlock blokuje requesty
**Rozwiązanie:** Wyłącz adblocki lub dodaj localhost do wyjątków

### Błąd: "Service Worker Update Failed"
**Problem:** Stary SW w cache
**Rozwiązanie:** 
```javascript
// DevTools → Application → Service Workers → Unregister
// Lub Hard Refresh: Ctrl+Shift+R
```

### Błąd: QR pokazuje się jako tekst a nie obraz
**Problem:** Lokalny fallback działa, ale wygląd CSS jest zły
**Rozwiązanie:** To normalne! Lokalny fallback to placeholder. Zewnętrzne API jest zablokowane.

---

## Podsumowanie Poprawek

| Plik | Co naprawiono | Status |
|------|---------------|--------|
| `app.py` | CSP `connect-src` z `api.qrserver.com` | ✅ |
| `deploy_ubuntu.sh` | CSP `connect-src` z `api.qrserver.com` | ✅ |
| `static/qr.js` | Error handling + lokalny fallback | ✅ |
| `static/qr.html` | Poprawna rejestracja SW | ✅ |
| `static/pokaz_qr.html` | Poprawna rejestracja SW | ✅ |
| `static/manifest.json` | Poprawny scope i ścieżki | ✅ |

**TERAZ WSZYSTKO POWINNO DZIAŁAĆ!** 🎉

Uruchom: `flask run` i otwórz `http://localhost:5000/static/test_qr.html`
