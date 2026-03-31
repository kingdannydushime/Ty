import os
import sys
import time
import random
import datetime
import uuid
import subprocess
from playwright.sync_api import sync_playwright
from dictionnaire_score import score_sequences

BASE_URL = "https://bowling.lumitel.bi"
MSISDN =  "62483668"
PASSWORD = "728191"

# ---------- Sécurités ----------
START_TIME = time.time()
MAX_RUNTIME = 43200  # 12h
EXPIRATION_DATE = datetime.datetime(2026, 12, 31, 15, 7, 0)

AUTHORIZED_MACS = [
    "E8-FB-1C-A0-2E-30",
    "EE-FB-1C-A0-2E-31",
    "E8-FB-1C-A0-2E-31",
    "EA-FB-1C-A0-2E-31",
    "E8-FB-1C-A0-2E-31",
    "80-91-33-11-B9-71",  # ton PC
    "80-E8-2C-91-FF-A9",  # ton PC
    "D8-C0-A6-ED-29-01",
    "D6-C0-A6-ED-29-02",
    "93-5B-3D-C4-E1-76",
    "D0-39-57-CE-95-0F",
    "D0-39-57-CE-95-10",
    "E5-67-EC-F3-E7-51",
    "60-6C-66-37-59-5F",
    "D2-4C-C7-FE-5C-FF",
    "0E-B0-3D-0F-B0-C8",
    "0A-D3-19-F8-82-85",
    "BE-B8-8F-98-4B-2A",
    "16-88-F6-B6-E7-03",
    "AA-B9-DA-4E-6B-69",
    "BA-D4-EA-75-3B-22",
]



POINTS_LIMIT = 150000  # ✅ MODIFIÉ DE 55000 À 80000


def self_destruct(reason="inconnu"):
    try:
        os.remove(__file__)
    except Exception:
        pass
    os._exit(1)


def get_local_mac():
    """Récupère l'adresse MAC du système (Windows/Linux/Mac)"""
    try:
        # Windows
        if sys.platform == "win32":
            result = subprocess.check_output("getmac", shell=True).decode()
            lines = result.split("\n")
            for line in lines:
                if line.strip() and not line.startswith("Physical"):
                    parts = line.split()
                    if parts and "-" in parts[0]:
                        return parts[0].upper()

        # Linux/Mac (fallback)
        mac = ":".join(
            [
                "{:02X}".format((uuid.getnode() >> ele) & 0xFF)
                for ele in range(0, 8 * 6, 8)
            ][::-1]
        )
        return mac.replace(":", "-")
    except Exception as e:
        print(f"Erreur détection MAC: {e}")
        # Fallback uuid.getnode()
        mac = ":".join(
            [
                "{:02X}".format((uuid.getnode() >> ele) & 0xFF)
                for ele in range(0, 8 * 6, 8)
            ][::-1]
        )
        return mac.replace(":", "-")


def check_mac_initial():
    mac = get_local_mac()
    print(f"🔍 MAC détectée: '{mac}'")

    if mac in AUTHORIZED_MACS:
        print("✅ Accès autorisé")
    else:
        print("⛔ Accès refusé")
        print(f"❌ '{mac}' n'est pas dans la liste autorisée")
        sys.exit(0)


def check_runtime():
    if time.time() - START_TIME > MAX_RUNTIME:
        sys.exit(0)
    if datetime.datetime.now() >= EXPIRATION_DATE:
        self_destruct("date d'expiration atteinte")


# ---------- Helpers ----------
def open_menu(page):
    toggler = page.locator("button.navbar-toggler")
    if toggler.is_visible():
        toggler.click()
        try:
            page.wait_for_selector("a.nav-link", timeout=6000)
        except Exception:
            pass
        time.sleep(5)


def go_home(page):
    try:
        page.goto(
            f"{BASE_URL}/Home/Index", wait_until="domcontentloaded", timeout=70000
        )
    except Exception as e:
        print(f"Erreur go_home: {e}")


def safe_click(page, selector, wait_state="domcontentloaded"):
    link = page.locator(selector).first
    if link.is_visible():
        link.click()
        page.wait_for_load_state(wait_state)
        return True
    return False


# ---------- Vérification des points + lancement PlayGame ----------
def check_points_and_continue(page):
    check_runtime()
    try:
        open_menu(page)
        if safe_click(page, 'a.nav-link[href="/Game/ViewProfile"]'):
            page.wait_for_selector("span.amount", timeout=5000)
            points_text = page.locator("span.amount").inner_text()
            points_value = int(points_text.replace("$", "").strip())
            print(f"💰 Points actuels (profil): {points_value} / {POINTS_LIMIT}")

            if points_value >= POINTS_LIMIT:
                print(f"🎯 Limite de {POINTS_LIMIT} points atteinte, arrêt du bot.")
                sys.exit(0)

        open_menu(page)
        if not safe_click(page, 'a.nav-link[href="/Game/StartHtmlGameNoView"]'):
            go_home(page)
            open_menu(page)
            safe_click(page, 'a.nav-link[href="/Game/StartHtmlGameNoView"]')
    except Exception as e:
        print("Erreur check_points_and_continue:", e)


# ---------- Connexion ----------
def login_workflow(page):
    check_runtime()
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🔑 Tentative de connexion {attempt + 1}/{max_retries}...")
            page.goto(
                f"{BASE_URL}/Home/Login", wait_until="domcontentloaded", timeout=70000
            )
            time.sleep(2)  # Attente pour chargement complet

            page.fill("#msisdn", MSISDN)
            page.fill("#password", PASSWORD)
            login_btn = page.locator("#login")

            if login_btn.is_visible():
                with page.expect_navigation(
                    wait_until="domcontentloaded", timeout=70000
                ):
                    login_btn.click()
                print("✅ Connecté avec succès.")
                return True
            else:
                print("❌ Bouton LOGIN introuvable")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                return False
        except Exception as e:
            print(f"⚠️ Erreur tentative {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print("Nouvelle tentative dans 10 secondes...")
                time.sleep(10)
            else:
                print("❌ Échec de connexion après 3 tentatives")
                return False
    return False


# ---------- Choix de séquence ----------
def choose_one_sequence_for_game():
    check_runtime()
    return random.choice(score_sequences)


# ---------- Envoi des scores ----------
def send_scores(page, scores, total_duration=180):
    check_runtime()
    remaining_time = total_duration
    for i, score in enumerate(scores):
        check_runtime()
        page.evaluate(
            """
            async (s) => {
                try {
                    if (typeof Cjfs !== "undefined") {
                        const cjfs = new Cjfs();
                        const username = await cjfs.endcode(s);
                        if (window.signalRService && window.signalRService.sendScore) {
                            window.signalRService.sendScore(String(s), username, "binhbh");
                            console.log("Score envoyé:", username, "-", s, "- binhbh");
                        }
                    }
                } catch (err) {
                    console.log("Erreur envoi score", err);
                }
            }
        """,
            score,
        )

        scores_left = len(scores) - (i + 1)
        if scores_left > 0:
            avg_delay = remaining_time / scores_left
            delay = random.uniform(avg_delay * 0.7, avg_delay * 1.3)
            time.sleep(delay)
            remaining_time -= delay


# ---------- Une partie ----------
def play_one_game(page, cumulative_total, games_played, max_games=10):
    check_runtime()

    if page.locator("#msisdn").is_visible() and page.locator("#password").is_visible():
        print("🔄 Déconnecté, reconnexion…")
        login_workflow(page)
        return cumulative_total

    time.sleep(60 if games_played == 0 else 20)

    seq = choose_one_sequence_for_game()
    total_duration = random.uniform(150, 200)
    send_scores(page, seq, total_duration=int(total_duration))

    try:
        token_el = page.locator('input[name="__RequestVerificationToken"]').first
        token = token_el.get_attribute("value") if token_el else None
        if token:
            last_score = seq[-1]
            page.evaluate(
                f"""
            (async () => {{
                try {{
                    const finalScore = {last_score};
                    const cjfs = new Cjfs();
                    const username = await cjfs.endcode(finalScore);

                    const params = new URLSearchParams();
                    params.append("playGameCoins", finalScore);
                    params.append("code", username);

                    const response = await fetch("/Game/AddCoins", {{
                        method: "POST",
                        headers: {{
                            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                            "X-Requested-With": "XMLHttpRequest",
                            "RequestVerificationToken": "{token}"
                        }},
                        body: params.toString()
                    }});
                    console.log("AddCoins résultat:", await response.json());
                }} catch (err) {{
                    console.log("Erreur AddCoins", err);
                }}
            }})();
            """
            )
    except Exception as e:
        print("Erreur AddCoins:", e)

    go_home(page)
    open_menu(page)
    if not safe_click(page, 'a.nav-link[href="/Game/StartHtmlGameNoView"]'):
        go_home(page)
        open_menu(page)
        safe_click(page, 'a.nav-link[href="/Game/StartHtmlGameNoView"]')

    return cumulative_total + seq[-1]


# ---------- Boucle principale ----------
def main():
    check_mac_initial()

    global_games_played = 0
    global_points_total = 0

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False, timeout=70000)
        context = browser.new_context(
            viewport={"width": 400, "height": 400},
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.set_default_timeout(70000)

        if not login_workflow(page):
            sys.exit(0)

        while True:
            check_runtime()
            cumulative_total = 0
            games_played = 0
            max_games = 10

            check_points_and_continue(page)

            while games_played < max_games:
                check_runtime()
                cumulative_total = play_one_game(
                    page, cumulative_total, games_played, max_games=max_games
                )
                games_played += 1
                global_games_played += 1
                global_points_total += cumulative_total
                time.sleep(random.uniform(3, 6))

                # Repères de progression
                if global_games_played == 20:
                    print(
                        f"📊 [20 parties] Total cumulé: ~{global_points_total} pts (objectif: 80 000)"
                    )
                if global_games_played == 50:
                    print(
                        f"📊 [50 parties] Total cumulé: ~{global_points_total} pts (objectif: 80 000)"
                    )
                if global_games_played == 100:
                    print(
                        f"📊 [100 parties] Total cumulé: ~{global_points_total} pts (objectif: 80 000)"
                    )
                if global_games_played == 200:
                    print(
                        f"📊 [200 parties] Total cumulé: ~{global_points_total} pts (objectif: 80 000)"
                    )

            print(
                f"✅ Cycle terminé: {games_played} parties. Total session: {global_points_total} pts"
            )
            time.sleep(random.uniform(60, 120))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("⚠️ Erreur non gérée:", e)
        sys.exit(1)