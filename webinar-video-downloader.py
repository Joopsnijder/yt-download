#!/usr/bin/env python3
"""
Script om video's te downloaden van webinar pagina's.
Ondersteunt verschillende video-platforms en embedded players.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
import subprocess
import sys
import json
import os


def setup_driver():
    """Configureer Chrome driver met juiste opties"""
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    # Verberg dat het een automated browser is
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Enable performance logging om network requests te zien
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=options)
    return driver


def find_video_urls(driver, url):
    """Vind video URLs op de pagina"""
    driver.get(url)
    print("Pagina geladen, wachten op video player...")

    # Wacht langer en probeer de video te starten
    time.sleep(10)

    video_urls = []

    # Probeer play button te vinden en te klikken
    try:
        print("Zoeken naar play button...")
        play_buttons = driver.find_elements(
            By.CSS_SELECTOR,
            "button[aria-label*='play'], button[class*='play'], .play-button, [class*='PlayButton']",
        )
        for button in play_buttons:
            try:
                print(f"Play button gevonden, proberen te klikken...")
                driver.execute_script("arguments[0].click();", button)
                time.sleep(3)
                break
            except:
                pass
    except Exception as e:
        print(f"Geen play button gevonden: {e}")

    # Wacht nog langer na play
    print("Wachten op video stream loading...")
    time.sleep(15)

    # Methode 1: Zoek naar video tags
    try:
        videos = driver.find_elements(By.TAG_NAME, "video")
        print(f"Gevonden {len(videos)} video tag(s)")
        for video in videos:
            src = video.get_attribute("src")
            if src and not src.startswith("blob:"):
                print(f"  Video src: {src}")
                video_urls.append(src)
            # Check voor source tags binnen video
            sources = video.find_elements(By.TAG_NAME, "source")
            for source in sources:
                src = source.get_attribute("src")
                if src and not src.startswith("blob:"):
                    print(f"  Source src: {src}")
                    video_urls.append(src)
    except Exception as e:
        print(f"Fout bij zoeken video tags: {e}")

    # Methode 2: Zoek naar iframe (Vimeo/YouTube embed)
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"Gevonden {len(iframes)} iframe(s)")
        for iframe in iframes:
            src = iframe.get_attribute("src")
            if src:
                print(f"  Iframe src: {src}")
                if any(
                    platform in src
                    for platform in [
                        "vimeo.com",
                        "youtube.com",
                        "wistia",
                        "jwplayer",
                        "cloudfront",
                    ]
                ):
                    video_urls.append(src)
    except Exception as e:
        print(f"Fout bij zoeken iframes: {e}")

    # Methode 3: Analyseer Chrome DevTools network logs
    print("\nAnalyseren network requests...")
    try:
        logs = driver.get_log("performance")
        for entry in logs:
            try:
                log = json.loads(entry["message"])["message"]
                if log["method"] == "Network.responseReceived":
                    resp_url = log["params"]["response"]["url"]
                    mime_type = log["params"]["response"].get("mimeType", "")

                    # Zoek naar video gerelateerde URLs
                    if any(
                        ext in resp_url
                        for ext in [
                            ".m3u8",
                            ".mp4",
                            ".webm",
                            ".ts",
                            "master.m3u8",
                            "playlist.m3u8",
                        ]
                    ):
                        # Geef prioriteit aan master.m3u8 of playlist met "master" in de naam
                        if (
                            "master" in resp_url.lower()
                            or "playlist" in resp_url.lower()
                        ):
                            print(f"  Network (MASTER): {resp_url}")
                        else:
                            print(f"  Network: {resp_url}")
                        video_urls.append(resp_url)
                    elif (
                        "video" in mime_type
                        or "mpegurl" in mime_type
                        or "audio" in mime_type
                    ):
                        print(f"  Network (mime: {mime_type}): {resp_url}")
                        video_urls.append(resp_url)
            except:
                pass
    except Exception as e:
        print(f"Fout bij analyseren network logs: {e}")

    # Methode 4: Check voor HLS streams in page source
    try:
        page_source = driver.page_source
        m3u8_pattern = r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
        m3u8_urls = re.findall(m3u8_pattern, page_source)
        if m3u8_urls:
            print(f"Gevonden {len(m3u8_urls)} m3u8 URL(s) in page source")
            video_urls.extend(m3u8_urls)
    except Exception as e:
        print(f"Fout bij zoeken in page source: {e}")

    # Filter uit manifest en andere niet-video bestanden
    filtered_urls = [
        url
        for url in video_urls
        if not any(
            skip in url for skip in ["manifest.webmanifest", "favicon", ".css", ".js"]
        )
    ]

    # Print alle gevonden m3u8 URLs voor analyse EN test ze op audio
    m3u8_urls = [u for u in filtered_urls if ".m3u8" in u]
    if m3u8_urls:
        print(f"\n📋 Gevonden {len(m3u8_urls)} m3u8 playlist(s):")
        import urllib.request

        for m3u8 in m3u8_urls:
            has_audio = "?"
            try:
                req = urllib.request.Request(m3u8)
                req.add_header(
                    "User-Agent",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                )
                req.add_header("Referer", "https://webinar.verzekeraars.nl/")
                with urllib.request.urlopen(req, timeout=3) as response:
                    content = response.read().decode("utf-8")
                    if "TYPE=AUDIO" in content or "AUDIO=" in content:
                        has_audio = "✓ AUDIO"
                    elif "#EXT-X-STREAM-INF" in content:
                        has_audio = "🔗 MASTER"
                    else:
                        has_audio = "✗ video-only"
            except:
                pass
            print(f"   [{has_audio}] {m3u8}")

    return list(set(filtered_urls))  # Verwijder duplicaten


def download_with_ytdlp(url, output_file="webinar_video.mp4"):
    """Download video met yt-dlp (werkt voor de meeste platforms)"""
    try:
        cmd = [
            "yt-dlp",
            "-o",
            output_file,
            "--verbose",  # Laat alle details zien
            "--user-agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "--referer",
            "https://webinar.verzekeraars.nl/",
            "--no-check-certificate",
            "--add-header",
            "Accept:*/*",
            "--add-header",
            "Accept-Language:nl-NL,nl;q=0.9,en;q=0.8",
            "--fragment-retries",
            "infinite",  # Blijf proberen bij netwerkfouten
            "--retries",
            "infinite",
            url,
        ]

        print(f"Downloaden met yt-dlp: {url}")
        print("=" * 50)
        # Laat de output direct zien zodat je de progress kunt volgen
        result = subprocess.run(cmd)

        if result.returncode == 0:
            print("=" * 50)
            print(f"✓ Video succesvol gedownload naar: {output_file}")
            return True
        else:
            print("=" * 50)
            print(f"✗ Download mislukt met return code: {result.returncode}")
            return False
    except FileNotFoundError:
        print("✗ yt-dlp niet geïnstalleerd. Installeer met: pip install yt-dlp")
        return False


def check_for_master_playlist(m3u8_url):
    """Probeer een master playlist te vinden die audio bevat"""
    import urllib.request

    potential_masters = []

    # Extract base directory
    base_dir = m3u8_url.rsplit("/", 1)[0]

    # Probeer verschillende master playlist locaties
    potential_masters.append(f"{base_dir}/master.m3u8")
    potential_masters.append(f"{base_dir}/index.m3u8")
    potential_masters.append(f"{base_dir}/playlist.m3u8")

    # Ook een niveau hoger proberen
    parent_dir = base_dir.rsplit("/", 1)[0]
    potential_masters.append(f"{parent_dir}/master.m3u8")
    potential_masters.append(f"{parent_dir}/index.m3u8")

    print(f"\n🔍 Zoeken naar master playlist met audio...")

    for master_url in potential_masters:
        try:
            req = urllib.request.Request(master_url)
            req.add_header(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                content = response.read().decode("utf-8")
                # Check of het een master playlist is met audio
                if "TYPE=AUDIO" in content or "AUDIO=" in content:
                    print(f"✓ Master playlist gevonden met audio: {master_url}")
                    return master_url
                elif "#EXT-X-STREAM-INF" in content:
                    print(
                        f"  Master playlist gevonden (zonder audio tag): {master_url}"
                    )
                    return master_url
        except:
            continue

    print("⚠️  Geen master playlist gevonden")
    return None


def download_m3u8_with_ffmpeg(
    m3u8_url, output_file="webinar_video.mp4", test_mode=False
):
    """Download HLS stream met ffmpeg"""
    try:
        # Test eerst wat er in de m3u8 zit
        print(f"\n🔍 Analyseren m3u8 playlist: {m3u8_url}")
        import urllib.request

        playlist_content = None
        try:
            req = urllib.request.Request(m3u8_url)
            req.add_header(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )

            with urllib.request.urlopen(req) as response:
                playlist_content = response.read().decode("utf-8")
                print("📋 Playlist inhoud (eerste 20 regels):")
                for i, line in enumerate(playlist_content.split("\n")[:20], 1):
                    if line.strip():
                        print(f"  {i:2}. {line}")

                # Check voor audio stream
                has_audio_indicator = any(
                    keyword in playlist_content.lower()
                    for keyword in ["audio", "sound", "TYPE=AUDIO"]
                )
                if has_audio_indicator:
                    print("✓ Audio stream referentie gevonden in playlist")
                else:
                    print("⚠️  Geen audio stream referentie gevonden in playlist")

                    # Probeer master playlist te vinden
                    master_url = check_for_master_playlist(m3u8_url)
                    if master_url and master_url != m3u8_url:
                        print(f"🔄 Gebruik master playlist in plaats van huidige")
                        m3u8_url = master_url
        except Exception as e:
            print(f"⚠️  Kan playlist niet lezen: {e}")

        # Eerste poging met codec copy (snelst)
        cmd = [
            "ffmpeg",
            "-y",
            "-user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "-headers",
            "Referer: https://webinar.verzekeraars.nl/",
            "-i",
            m3u8_url,
        ]

        # Test mode: download alleen eerste 30 seconden
        if test_mode:
            cmd.extend(["-t", "30"])
            print("\n⚡ TEST MODE: Downloaden eerste 30 seconden...")

        cmd.extend(
            [
                "-c",
                "copy",
                "-bsf:a",
                "aac_adtstoasc",
                "-progress",
                "pipe:1",  # Progress naar stdout
                "-loglevel",
                "error",  # Alleen errors, niet alle ts files
                "-stats",  # Show stats
                output_file,
            ]
        )

        print(f"\n🎬 Downloaden HLS stream...")
        print("=" * 50)
        result = subprocess.run(cmd)

        if result.returncode == 0:
            # Check of er audio is
            print("\n🔍 Controleren streams in gedownloade video...")
            check_cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,codec_name",
                "-of",
                "json",
                output_file,
            ]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)

            try:
                streams_info = json.loads(check_result.stdout)
                video_streams = [
                    s
                    for s in streams_info.get("streams", [])
                    if s["codec_type"] == "video"
                ]
                audio_streams = [
                    s
                    for s in streams_info.get("streams", [])
                    if s["codec_type"] == "audio"
                ]

                print(f"📹 Video streams: {len(video_streams)}")
                for vs in video_streams:
                    print(f"   - {vs.get('codec_name', 'unknown')}")

                print(f"🔊 Audio streams: {len(audio_streams)}")
                for aus in audio_streams:
                    print(f"   - {aus.get('codec_name', 'unknown')}")

                if audio_streams:
                    print("=" * 50)
                    print(f"✓ Video succesvol gedownload naar: {output_file}")
                    print("✓ Audio stream aanwezig")
                    return True
                else:
                    print("\n⚠️  Geen audio stream gevonden!")
                    print("Dit kan betekenen dat:")
                    print(
                        "  1. De video origineel geen audio heeft (opname zonder geluid)"
                    )
                    print("  2. Audio zit in een aparte m3u8 playlist")
                    print(
                        "  3. De browser gebruikte een andere URL die wij niet detecteerden"
                    )
                    print("\n💡 Tip: Open de pagina in Chrome DevTools -> Network tab")
                    print(
                        "    Filter op 'm3u8' en kijk of je MEERDERE playlists ziet laden"
                    )
                    print("    (een voor video, een voor audio)")
                    return True  # Video werkt, alleen geen audio
            except Exception as e:
                print(f"⚠️  Kan streams niet analyseren: {e}")
                return True
        else:
            print("=" * 50)
            print(f"✗ Download mislukt met return code: {result.returncode}")
            return False
    except FileNotFoundError:
        print("✗ ffmpeg niet geïnstalleerd. Installeer ffmpeg eerst.")
        return False


def main():
    url = "https://www.youtube.com/watch?v=15Z5nsyLDbE"

    # Check voor test mode argument
    test_mode = "--test" in sys.argv or "-t" in sys.argv

    print("Video downloader voor webinar pagina's")
    print("=" * 50)
    print(f"URL: {url}")
    if test_mode:
        print("⚡ TEST MODE: Download alleen eerste 30 seconden")
    print()

    # Stap 1: Setup browser en vind video URLs
    print("Stap 1: Browser openen en video URLs zoeken...")
    driver = setup_driver()

    try:
        video_urls = find_video_urls(driver, url)

        if not video_urls:
            print("✗ Geen video URLs gevonden op de pagina")
            print("\nProbeer handmatig:")
            print("1. Open de pagina in Chrome")
            print("2. Open Developer Tools (F12)")
            print("3. Ga naar Network tab")
            print("4. Filter op 'Media' of zoek naar .m3u8/.mp4")
            print("5. Speel de video af en kijk welke URLs geladen worden")
        else:
            print(f"✓ {len(video_urls)} video URL(s) gevonden:\n")
            for i, video_url in enumerate(video_urls, 1):
                print(f"{i}. {video_url[:100]}...")

            # Stap 2: Probeer te downloaden
            print("\nStap 2: Video downloaden...")

            # Sorteer: m3u8 eerst, dan mp4, dan de rest
            def url_priority(url):
                if ".m3u8" in url:
                    return 0
                elif ".mp4" in url:
                    return 1
                elif ".ts" in url:
                    return 3
                else:
                    return 2

            sorted_urls = sorted(video_urls, key=url_priority)

            # Als we .ts segmenten vinden, probeer de m3u8 playlist af te leiden
            ts_urls = [u for u in video_urls if ".ts" in u]
            if ts_urls and not any(".m3u8" in u for u in video_urls):
                print(
                    "\n⚠️  Alleen .ts segmenten gevonden, probeer m3u8 playlist af te leiden..."
                )
                # Van: /recordings/xxx/yyy-00.ts -> /recordings/xxx/yyy.m3u8
                for ts_url in ts_urls:
                    # Probeer verschillende varianten
                    potential_playlists = []

                    # Variant 1: vervang -00.ts met .m3u8
                    variant1 = re.sub(r"-\d+\.ts$", ".m3u8", ts_url)
                    if variant1 != ts_url:
                        potential_playlists.append(variant1)

                    # Variant 2: master.m3u8 in dezelfde directory
                    base_url = ts_url.rsplit("/", 1)[0]
                    potential_playlists.append(f"{base_url}/master.m3u8")
                    potential_playlists.append(f"{base_url}/playlist.m3u8")

                    for m3u8_url in potential_playlists:
                        if m3u8_url not in sorted_urls:
                            print(f"   Probeer: {m3u8_url}")
                            sorted_urls.insert(0, m3u8_url)

            print(f"\nProbeer {len(sorted_urls)} URL(s) in volgorde van prioriteit:")
            for i, url in enumerate(sorted_urls, 1):
                url_type = (
                    "M3U8 playlist"
                    if ".m3u8" in url
                    else "MP4"
                    if ".mp4" in url
                    else "TS segment"
                    if ".ts" in url
                    else "Andere"
                )
                print(f"{i}. [{url_type}] {url[:80]}...")

            for video_url in sorted_urls:
                if ".m3u8" in video_url:
                    # Voor HLS streams, gebruik ffmpeg (of yt-dlp)
                    if download_m3u8_with_ffmpeg(video_url, test_mode=test_mode):
                        break
                    elif download_with_ytdlp(video_url):
                        break
                elif ".mp4" in video_url:
                    if download_with_ytdlp(video_url):
                        break
                else:
                    # Skip .ts segmenten tenzij het de enige optie is
                    if video_url == sorted_urls[-1]:
                        print(f"\n⚠️  Laatste poging met: {video_url}")
                        if download_with_ytdlp(video_url):
                            break

    finally:
        driver.quit()
        print("\nBrowser gesloten.")


if __name__ == "__main__":
    # Installatie instructies
    print("\nVereiste software:")
    print("1. pip install selenium")
    print("2. pip install yt-dlp")
    print("3. Chrome browser")
    print("4. ChromeDriver (download van https://chromedriver.chromium.org/)")
    print("5. ffmpeg (optioneel, voor HLS streams)")
    print("\nOpties:")
    print("  --test of -t : Download alleen eerste 30 seconden (voor testen)\n")

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Script onderbroken door gebruiker")
    except Exception as e:
        print(f"\n✗ Fout opgetreden: {e}")
        print("\nControleer of alle vereiste software geïnstalleerd is.")
