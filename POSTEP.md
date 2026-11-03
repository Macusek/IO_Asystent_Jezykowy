# Postęp — 3 listopada 2026

## Stan

Wszystkie siedem etapów implementacji ukończono w kolejności z planu. Checklistę w lokalnym PLAN_APLIKACJI.md zaktualizowano. Przeczytano cały plan i wszystkie 7 stron PDF, obejrzano diagramy UML, architekturę i mock interfejsu. Nie znaleziono istotnych sprzeczności nierozstrzygniętych planem.

## Etapy i weryfikacja

1. Szkielet, zależności, schemat SQLite, .gitignore i przykład klucza. Utworzono bazę. Klucz wykluczono przed wdrożeniem jego odczytu.
2. Rejestracja, logowanie, Argon2id, sesje serwerowe, wylogowanie, reset hasła z wygasaniem i jednorazowym tokenem. 4 testy passed.
3. PL/EN/ES × A1–C2, zapis i wznowienie rozmowy, trwałe wiadomości, kontrola właściciela. 5 testów passed.
4. Wyłącznie Groq openai/gpt-oss-120b, odczyt pierwszej niepustej linii pliku, walidacja kontraktu, timeouty, 401/403, 429, 5xx i ograniczone retry; stub oraz MockTransport. 21 testów passed.
5. Zakończenie i lista korekt, informacja o wiadomościach nieocenionych, zakaz wysyłania po zakończeniu, idempotentne zakończenie. 22 testy passed; składnia JS poprawna.
6. Statystyki skumulowane, unikalne słowa jako zbiór, sekundy / 60, zero czasu i brak ocen, reset per użytkownik/język bez podwójnego naliczania. 25 testów passed.
7. Pełny zestaw reguł, ochrona przed rzeczywistym HTTP w testach, przypadki brzegowe tekstu, błędne odpowiedzi, restart bazy, SMTP na atrapie, blokada równoległych tur, test wymogu klucza mimo zmiennej środowiskowej. README po polsku i wersje zależności w requirements-lock.txt.

## Wynik końcowy

- `python -m pytest -q --basetemp=tmp/final-tests --tb=short`: **46 passed**, 1 ostrzeżenie biblioteki Starlette o przyszłej migracji klienta testowego z httpx na httpx2. Brak błędów testów.
- `node --check app/static/app.js`: poprawna składnia.
- `python -m app.db`: baza gotowa; ponowna inicjalizacja zachowuje dane.
- `python -m pip check`: brak konfliktów zależności.
- Test Playwright na Microsoft Edge, bez okna: **PASS** — rejestracja, logowanie, wybór ES/A2, zapis i odpowiedź stuba, zachowanie wiadomości przy symulowanej awarii, korekty, statystyki, reset, wylogowanie. Brak błędów JavaScript. Obejrzano zrzuty wszystkich pięciu podstawowych ekranów w tmp/ui/.
- Normalne `python -m app.main` bez pliku klucza: oczekiwany błąd i zakończenie startu. Testy nie wymagają klucza.
- `git check-ignore groq_api_key.txt`: potwierdzono wykluczenie. Repozytorium nie miało commitów; niczego nie commitowano, nie używano rzeczywistego klucza.

## Uwagi środowiskowe

Systemowe aliasy python / py były niedostępne. Użyto dostarczonego Pythona 3.12 do utworzenia .venv, następnie zainstalowano zależności i pip w lokalnym środowisku. Instalacja zależności wymagała wyjścia poza ograniczenie sieci piaskownicy. TestClient w piaskownicy Windows zawieszał się przy tworzeniu lokalnego socketpair asyncio; testy uruchomione poza piaskownicą przeszły. Początkowy test UI miał zbyt ścisły selektor tekstu zawierającego etykietę AI; poprawiono selektor i powtórzono cały przepływ z wynikiem PASS. Wcześniejsze zawieszone procesy testowe zatrzymano, serwer testowy zamknięto.

## Co pozostaje do ręcznej weryfikacji

Brak blokad implementacji. Użytkownik musi utworzyć groq_api_key.txt z rzeczywistym kluczem i uruchomić `python -m app.main` z lokalnego środowiska. Rzeczywiste API Groq nie było wywoływane. Do sprawdzenia: dostępność modelu na koncie, jakość korekt i dialogu w 3 językach na 6 poziomach, zgodność odpowiedzi z kontraktem, rzeczywista latencja i limity. Dostarczenie e-maila przez prawdziwy SMTP także nie było weryfikowane; ścieżka aplikacji jest sprawdzona atrapą.

## Zmiana widoku czatu

Powiększono czat do pełnej szerokości strony z szerszą kolumną rozmowy i wyższą historią. Podczas rozmowy ukryto hasło promocyjne. Po prawej dodano panel korekt aktualizowany po każdej ocenionej turze, pobierany z endpointu rozmowy z kontrolą właściciela. Na węższym oknie panel przechodzi pod czat. Przy opuszczaniu rozmowy przywracany jest zwykły układ.
Weryfikacja: 46 testów passed (1 wcześniejsze ostrzeżenie Starlette), składnia JS OK, Playwright/Edge PASS z kontrolą szerokości, położenia panelu, korekt przed zakończeniem oraz przywracania układu po zakończeniu. Obejrzano zrzut czatu. Użyto wyłącznie stuba. Aby załadować zmieniony backend, należy zrestartować działający serwer, a następnie odświeżyć stronę.
