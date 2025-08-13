#!/usr/bin/env python3
"""
YouTube to MP3 downloader using yt-dlp
"""

import yt_dlp
import sys
import os

def download_mp3(url, output_dir="."):
    """Download MP3 from YouTube URL"""
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'audioquality': '192',
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        # SSL configuration to handle certificate issues
        'nocheckcertificate': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading: {url}")
            ydl.download([url])
            print("Download completed successfully!")
            
    except Exception as e:
        print(f"Error downloading: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    # Default URL or get from command line
    url = "https://youtu.be/N5svR6NCTFg?si=LwjPD2P7h5pG-dwr"
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    print(f"YouTube to MP3 Downloader")
    print(f"URL: {url}")
    
    # Create downloads directory
    downloads_dir = "downloads"
    os.makedirs(downloads_dir, exist_ok=True)
    
    success = download_mp3(url, downloads_dir)
    
    if success:
        print(f"File saved to: {downloads_dir}/")
    else:
        sys.exit(1)