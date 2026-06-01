#!/usr/bin/env python3
import subprocess
import sys


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=15Z5nsyLDbE"

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "-o", "%(title)s.mp4",
        url,
    ]

    print(f"Downloaden: {url}")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("Download mislukt")
        sys.exit(1)


if __name__ == "__main__":
    main()
