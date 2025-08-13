# YouTube to MP3 Downloader

A simple Python script to download MP3 audio from YouTube videos using yt-dlp.

## Features

- Download high-quality MP3 files from YouTube
- Automatic audio extraction and conversion
- SSL certificate handling for compatibility
- Downloads saved to organized folder structure

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Joopsnijder/yt-download.git
cd yt-download
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Download with default URL (hardcoded):
```bash
python main.py
```

### Download with custom URL:
```bash
python main.py "https://youtu.be/VIDEO_ID"
```

Downloaded MP3 files will be saved in the `downloads/` directory.

## Requirements

- Python 3.6+
- yt-dlp
- FFmpeg (for audio conversion)

## License

This project is for educational purposes only. Please respect YouTube's Terms of Service and copyright laws.