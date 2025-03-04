from flask import Flask, request, jsonify, render_template
import re
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import os
import time
from functools import wraps
from pytube import YouTube
import requests
from bs4 import BeautifulSoup
import random

# Configure Gemini API
api_key = os.getenv('GEMINI_API_KEY', "AIzaSyAL-dytEp5xgyB3TpwvXijz4xXXoBNjXTQ")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

app = Flask(__name__)

# List of user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
]

def get_random_headers():
    """Generate random headers to avoid detection."""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

def extract_video_id(youtube_url):
    """Extracts the YouTube video ID."""
    match = re.search(r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/)([a-zA-Z0-9_-]{11})", youtube_url)
    return match.group(1) if match else None

def get_transcript_method1(video_id):
    """Method 1: Using youtube_transcript_api."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        return ' '.join([t['text'] for t in transcript])
    except Exception as e:
        return None

def get_transcript_method2(video_id):
    """Method 2: Using pytube."""
    try:
        yt = YouTube(f'https://www.youtube.com/watch?v={video_id}')
        captions = yt.captions.get_by_language_code('en')
        if not captions:
            captions = yt.captions.all()[0]  # Get first available caption if English not available
        return captions.generate_srt_captions()
    except Exception as e:
        return None

def get_transcript_method3(video_id):
    """Method 3: Using direct HTTP request with rotating user agents."""
    try:
        url = f'https://www.youtube.com/watch?v={video_id}'
        headers = get_random_headers()
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find caption tracks in the page source
        scripts = soup.find_all('script')
        for script in scripts:
            if 'captionTracks' in str(script):
                return "Captions available but require authentication"
        return None
    except Exception as e:
        return None

def get_transcript(video_id):
    """Try multiple methods to get the transcript."""
    # Add delay between attempts
    time.sleep(1)
    
    # Try method 1 (youtube_transcript_api)
    transcript = get_transcript_method1(video_id)
    if transcript:
        return transcript
    
    # Try method 2 (pytube)
    transcript = get_transcript_method2(video_id)
    if transcript:
        return transcript
    
    # Try method 3 (direct request)
    transcript = get_transcript_method3(video_id)
    if transcript:
        return transcript
    
    return "Error: Unable to fetch transcript. This could be due to:\n1. No captions available\n2. Video is private or age-restricted\n3. YouTube API restrictions"

def format_prompt(transcript, style):
    """Formats the prompt for Gemini."""
    prompt_prefix = """Generate structured lecture notes from the following transcript:

- Format the notes into sections with bullet points.
- Use clear headings and subheadings.
- Summarize key concepts, definitions, and examples.
"""
    prompt_suffix = {
        "concise": "- Keep the notes brief and to the point.",
        "detailed": "- Provide comprehensive explanations and examples.",
        "key_points": "- Focus on the most important concepts and takeaways.",
        "default": ""
    }.get(style, "")
    return f"{prompt_prefix}\n{prompt_suffix}\n\nLecture Transcript:\n{transcript}"

def generate_notes(transcript, style):
    """Generates lecture notes using Gemini."""
    prompt = format_prompt(transcript, style)
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating notes: {e}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate_notes', methods=['POST'])
def generate():
    data = request.json
    youtube_url = data.get('youtube_url')
    style = data.get('style', 'default')
    
    if not youtube_url:
        return jsonify({"error": "Please enter a YouTube URL."}), 400
    
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL."}), 400
    
    transcript = get_transcript(video_id)
    if transcript.startswith("Error"):
        return jsonify({"error": transcript}), 400
    
    notes = generate_notes(transcript, style)
    if "Error" in notes:
        return jsonify({"error": notes}), 500
    
    return jsonify({"notes": notes})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
