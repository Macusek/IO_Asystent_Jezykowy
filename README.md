# LanguageMate — nauka języków przez rozmowę z AI

Lokalna aplikacja przeglądarkowa: Python 3.12+, FastAPI, SQLite i HTML/CSS/JavaScript bez frameworka SPA. Interfejs jest po polsku. Rozmowy: polski, angielski i hiszpański, poziomy CEFR A1–C2. Jedyny model to `openai/gpt-oss-120b`, wywoływany przez backend pod adresem `https://api.groq.com/openai/v1`.

## Instalacja i baza

Otwórz terminal w katalogu projektu. Zainstaluj Python 3.12 lub nowszy z [python.org](https://www.python.org/downloads/). Nie jest potrzebny Node.js do uruchomienia aplikacji ani testów Pythona.

Windows, PowerShell (komendy nie wymagają aktywacji środowiska ani zmiany ExecutionPolicy):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.db
```

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m app.db
```

Baza `data/app.sqlite3` powstaje także automatycznie podczas startu serwera. Schemat jest inicjalizowany bez usuwania danych. Katalog `data/` jest wykluczony z Git; zawiera dane kont, sesje i rozmowy, więc traktuj go jako prywatny. Kopię bazy wykonuj przy wyłączonym serwerze.

`requirements-lock.txt` zapisuje dokładne wersje użyte do weryfikacji na Pythonie 3.12. Aby je odtworzyć, użyj w komendzie instalacji `-r requirements-lock.txt` zamiast `-r requirements.txt`.

## Konto Groq i klucz

1. Załóż konto lub zaloguj się w [konsoli Groq](https://console.groq.com/).
2. Otwórz [API Keys](https://console.groq.com/keys) i wygeneruj klucz. Konto musi mieć dostęp do wskazanego modelu i dostępny limit.
3. W katalogu projektu utwórz `groq_api_key.txt`. Wklej **sam klucz**, bez cudzysłowów i bez opisu. Zapisz plik jako UTF-8. Możesz skopiować plik `.example`, ale usuń z kopii instrukcję i zastąp ją kluczem.

Windows:

```powershell
Copy-Item groq_api_key.txt.example groq_api_key.txt
notepad groq_api_key.txt
```

macOS / Linux:

```bash
cp groq_api_key.txt.example groq_api_key.txt
nano groq_api_key.txt
chmod 600 groq_api_key.txt
```

Klient czyta pierwszą niepustą linię przy starcie. Nie czyta klucza ze zmiennych środowiskowych ani `.env`. Brak, pusty lub błędnie sformatowany plik blokuje normalny start czytelnym komunikatem. Po zmianie klucza uruchom serwer ponownie. Nigdy nie wklejaj go do kodu, przeglądarki ani Git. `.gitignore` wyklucza rzeczywisty plik; przykład nie zawiera sekretu.

## Uruchomienie

Windows:

```powershell
.\.venv\Scripts\python.exe -m app.main
```

macOS / Linux:

```bash
.venv/bin/python -m app.main
```

Otwórz [http://127.0.0.1:8000](http://127.0.0.1:8000). Zarejestruj konto (e-mail i hasło 10–128 znaków), zaloguj się, wybierz język i poziom, naciśnij „Rozpocznij”. Napisz pierwszą wiadomość — każda wysłana tura wywołuje Groq z historią rozmowy. „Zakończ rozmowę” otwiera korekty i podsumowanie. „Statystyki” pokazują wyniki konta dla wybranego języka. Przerwaną aktywną rozmowę można wznowić po ponownym zalogowaniu lub odświeżeniu strony. Zatrzymanie serwera: Ctrl+C.

Serwer nasłuchuje lokalnie, w jednym procesie. Blokady serializują operacje tury i zakończenia w obrębie rozmowy. Nie uruchamiaj wielu workerów bez dodania blokad między procesami. Do pracy przez HTTPS ustaw `--secure-cookie` i właściwy `--public-url`; domyślna konfiguracja jest przeznaczona na własny komputer.

## Reset hasła

Token jest losowy, ważny 30 minut i jednorazowy. Baza przechowuje jego skrót. Wygenerowanie nowego linku unieważnia poprzednie; zmiana hasła unieważnia wszystkie sesje konta i tokeny resetu. Hasła są hashowane Argon2id.

**Jawny tryb deweloperski bez SMTP:**

```powershell
.\.venv\Scripts\python.exe -m app.main --dev
```

```bash
.venv/bin/python -m app.main --dev
```

Kliknij „Zapomniałem hasła” i podaj e-mail istniejącego konta. Link pojawi się wyłącznie w terminalu serwera z oznaczeniem „TRYB DEWELOPERSKI”. Otwórz go w przeglądarce i ustaw nowe hasło. Link jest sekretem; nie udostępniaj logu. Interfejs nie ujawnia tokenu. Bez `--dev` i bez SMTP funkcja zwraca komunikat o konieczności konfiguracji, zamiast udawać wysłanie poczty. Klucz Groq jest nadal wymagany do normalnego uruchomienia serwera, także z `--dev`.

**SMTP:** skopiuj `smtp_config.json.example` do `smtp_config.json` i uzupełnij host, port, nadawcę, login i hasło. Rzeczywisty plik jest wykluczony z Git. Aplikacja używa SMTP z STARTTLS (np. port 587), nie implicit TLS na porcie 465. Jeśli serwer wymaga hasła aplikacji, podaj je w konfiguracji. Przykładowe uruchomienie:

```powershell
.\.venv\Scripts\python.exe -m app.main --smtp-config smtp_config.json --public-url http://127.0.0.1:8000
```

```bash
.venv/bin/python -m app.main --smtp-config smtp_config.json --public-url http://127.0.0.1:8000
```

W trybie SMTP link jest wysyłany e-mailem i nie jest logowany, również przy `--dev`. Błąd wysłania jest zgłaszany użytkownikowi. Z rzeczywistym serwerem SMTP należy sprawdzić dostarczenie wiadomości.

## Reguły analizy i statystyk

- Zdania rozdzielają `.`, `!`, `?` oraz nowa linia. Kolejne znaki kończące tworzą jeden separator. Zachowujemy interpunkcję w tekście zdania i usuwamy skrajne odstępy. Fragment bez końcowej kropki też jest zdaniem, jeśli zawiera słowo. Fragmenty z samą interpunkcją lub cyframi są pomijane. To deterministyczna reguła, nie pełny parser językowy: skróty i liczby dziesiętne mogą rozdzielać zdania (np. `Dr. Smith` to dwa fragmenty). Te same fragmenty otrzymuje model i walidator.
- Słowo to ciąg liter Unicode, opcjonalnie z wewnętrznym apostrofem lub łącznikiem (`don't`, `e-mail`). Cyfry, emoji i podkreślenia nie są słowami. Normalizacja NFC i `casefold` ignorują wielkość liter; apostrof typograficzny normalizujemy do prostego. Akcenty zachowujemy, więc `si` i `sí` są różnymi słowami.
- Unikalne słowa to zbiór słów użytkownika ze wszystkich objętych raportem rozmów — nie suma unikalnych słów w poszczególnych rozmowach. Wypowiedzi AI nie zwiększają liczników.
- Model zwraca `reply` i listę `errors` (`sentence_index`, `zdanie`, `korekta`, `opis`). Ścisła walidacja wymaga prawidłowych typów, niepustych pól i dokładnego przypisania do zdania użytkownika. Dodatkowe pola i niepoprawne indeksy odrzucamy. Kilka korekt przypisanych do jednego indeksu to **jedno błędne zdanie**; dwa identycznie brzmiące zdania z różnymi indeksami to dwa zdania.
- Tylko poprawnie ocenione tury zwiększają liczniki zdań poprawnych i błędnych. Nieocenione zdania mają osobny licznik. Wszystkie zapisane słowa użytkownika, również z nieocenionych tur, zwiększają liczbę słów i zbiór unikalnych słów.
- Procent błędów = błędne / (poprawne + błędne) × 100. Przy braku ocen wyświetlamy 0 i informację o braku ocenionych zdań.
- Tempo = wszystkie słowa użytkownika / (łączny czas zakończonych rozmów w sekundach / 60). Nie uśredniamy tempa poszczególnych rozmów. Czas od rozpoczęcia do zakończenia obejmuje oczekiwanie na AI i przerwy użytkownika. Dla zerowego czasu wynik wynosi 0. Dane w API zachowują precyzję, interfejs zaokrągla do jednego miejsca.
- Raport konta jest wyliczany z zakończonych rozmów. Nie dopisujemy drugi raz agregatów podczas ponownego zakończenia. Reset ustawia granicę czasu osobno dla konta i języka. Rozmowy zakończone przed resetem nie wracają do raportu; rozmowa aktywna w momencie resetu zostanie uwzględniona po zakończeniu. Reset nie kasuje wiadomości i korekt ani podsumowania rozmowy.

## Awaria Groq

Wiadomość użytkownika jest zatwierdzana w bazie przed żądaniem do Groq. Dopiero po pełnej walidacji odpowiedź AI i oceny są zapisywane atomowo. Awaria zachowuje wiadomość z oznaczeniem „nieoceniona”. Po awarii można kontynuować rozmowę; historia zawiera również nieocenioną wiadomość. Aplikacja nie ponawia automatycznie zapisanej tury po odświeżeniu strony. Tura przerwana zatrzymaniem procesu także pozostaje nieoceniona.

Timeout: połączenie 10 s, operacje HTTP 45 s. Maksymalnie dwa żądania: jedno ponowienie błędu połączenia lub 5xx; dla 429 tylko gdy `Retry-After` podaje czas od 0 do 2 sekund. Nie ponawiamy timeoutów odczytu, złego klucza ani błędnej struktury odpowiedzi. Komunikaty nie ujawniają klucza ani surowych błędów dostawcy. Kontrakt korzysta z [trybu JSON Groq](https://console.groq.com/docs/structured-outputs) i dodatkowej walidacji po stronie aplikacji; składnia JSON sama nie gwarantuje prawidłowej oceny językowej.

## Testy bez klucza i bez sieci

Po jednorazowej instalacji zależności testy nie potrzebują pliku klucza ani dostępu do internetu:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

```bash
.venv/bin/python -m pytest -q
```

Każdy test używa izolowanej bazy w `tmp/pytest`, wstrzykniętego stuba lub `httpx.MockTransport`. Automatyczna blokada rzeczywistego transportu HTTP wykrywa przypadkowe wyjście do sieci. SMTP jest testowany atrapą. TestClient potrzebuje systemowego lokalnego gniazda asyncio; w restrykcyjnej piaskownicy Windows uruchom testy w zwykłym terminalu. Testy stuba potwierdzają przepływ aplikacji, **nie działanie rzeczywistego Groq ani jakość korekt**.

Opcjonalny test prawdziwej przeglądarki wymaga Node.js, Playwright oraz Chromium. W osobnym terminalu uruchom `python tests/browser_server.py` (użyj Pythona z `.venv`), a potem `node tests/browser_smoke.cjs`. Serwer na porcie 8011 ma wyraźnie oznaczony stub i tymczasową bazę usuwaną po zamknięciu. Nie jest to normalny sposób uruchamiania aplikacji. Zrzuty ekranów trafiają do ignorowanego `tmp/ui/`.

Instalacja opcjonalnego narzędzia UI: `npm install --no-save playwright`, następnie `npx playwright install chromium`. Alternatywnie dla już zainstalowanego Edge ustaw `PLAYWRIGHT_CHANNEL=msedge` (PowerShell: `$env:PLAYWRIGHT_CHANNEL='msedge'`; macOS/Linux: `PLAYWRIGHT_CHANNEL=msedge node tests/browser_smoke.cjs`).

## Układ projektu

`app/auth.py` — konta, sesje i reset; `conversations.py` — rozmowy i atomowy przepływ tury; `llm.py` — wyłącznie Groq, klucz, kontrakt i błędy; `stats.py` — raport i reset; `text.py` — wspólne reguły tekstu; `db.py` — SQLite; `web.py` i `static/` — interfejs. `PLAN_APLIKACJI.md` zawiera aktualizowaną checklistę, `POSTEP.md` stan prac i weryfikacji.

## Do ręcznego sprawdzenia z rzeczywistymi usługami

Po dodaniu klucza sprawdź odpowiedzi i korekty w PL, EN i ES na poziomach A1–C2, zgodność odpowiedzi z kontraktem, czas oczekiwania i limity konta Groq. Sprawdź odrzucenie nieprawidłowego klucza oraz zachowanie przy niedostępnej sieci. Jeśli używasz SMTP, sprawdź dostarczenie linku i ukończenie resetu z wiadomości e-mail. Testy offline nie zastępują tych prób.
