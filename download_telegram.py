#!/usr/bin/env python3
import sys
import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import time

def download_file(url, output_path):
    """Download a file from a direct URL."""
    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ Downloaded: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to download {url}: {e}")
        return False

def extract_media_from_telegram(post_url):
    """Extract media file URL and text from a public Telegram post."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    resp = requests.get(post_url, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    # 1. Try to find video/meta tags
    media_url = None

    # Open Graph video
    meta_video = soup.find('meta', property='og:video')
    if meta_video and meta_video.get('content'):
        media_url = meta_video['content']
    else:
        # Open Graph image (for photos)
        meta_image = soup.find('meta', property='og:image')
        if meta_image and meta_image.get('content'):
            media_url = meta_image['content']
        else:
            # Look for direct video source in <video> tag
            video_tag = soup.find('video')
            if video_tag:
                src = video_tag.get('src')
                if src:
                    media_url = urljoin(post_url, src)
            if not media_url:
                # Look for document download link
                doc_link = soup.find('a', class_=re.compile(r'tgme_widget_message_document'))
                if doc_link and doc_link.get('href'):
                    media_url = doc_link['href']
                else:
                    # Sometimes the link is inside a data attribute
                    video_elem = soup.find(class_=re.compile(r'tgme_widget_message_video_player'))
                    if video_elem:
                        video_src = video_elem.get('data-video-src')
                        if video_src:
                            media_url = video_src

    # Extract text content
    text_div = soup.find('div', class_='tgme_widget_message_text')
    text_content = text_div.get_text(strip=True) if text_div else ""

    return media_url, text_content

def sanitize_filename(filename):
    """Remove invalid characters from filename."""
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def main():
    if len(sys.argv) < 2:
        print("Usage: python download_telegram.py <telegram_post_url>")
        sys.exit(1)

    post_url = sys.argv[1].strip()
    print(f"📥 Processing: {post_url}")

    # Create downloads directory if not exists
    os.makedirs("downloads", exist_ok=True)

    try:
        media_url, text = extract_media_from_telegram(post_url)

        if text:
            text_filename = os.path.join("downloads", "post_text.txt")
            with open(text_filename, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"📄 Text saved: {text_filename}")

        if media_url:
            # Determine file extension
            if '?' in media_url:
                media_url = media_url.split('?')[0]
            ext = os.path.splitext(media_url)[1]
            if not ext:
                ext = '.mp4'  # default for video
            # Create a sensible filename
            base_name = f"telegram_media_{int(time.time())}{ext}"
            output_path = os.path.join("downloads", sanitize_filename(base_name))
            download_file(media_url, output_path)
        else:
            print("⚠️ No media file found in this post.")
            if not text:
                print("❌ Neither media nor text could be extracted.")
                sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
