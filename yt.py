from flask import Flask, request, jsonify, render_template
import re
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import os
import time
import json
import yt_dlp
from dotenv import load_dotenv
import tempfile
from functools import wraps

# Load environment variables
load_dotenv()

# Configure Gemini API
api_key = os.getenv('GEMINI_API_KEY', "AIzaSyAL-dytEp5xgyB3TpwvXijz4xXXoBNjXTQ")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

app = Flask(__name__)

# Rate limiting decorator
def rate_limited(max_per_second):
    min_interval = 1.0 / float(max_per_second)
    def decorator(func):
        last_time_called = [0.0]
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_time_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_time_called[0] = time.time()
            return ret
        return wrapper
    return decorator

def extract_video_id(youtube_url):
    """Extracts the YouTube video ID."""
    match = re.search(r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/)([a-zA-Z0-9_-]{11})", youtube_url)
    return match.group(1) if match else None

def get_transcript_ytdlp(video_id):
    """Get transcript using yt-dlp."""
    try:
        url = f'https://www.youtube.com/watch?v={video_id}'
        
        # Configure yt-dlp
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }

        # Create a temporary directory for subtitle files
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts['paths'] = {'home': temp_dir}
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    # Try to get video info and subtitles
                    info = ydl.extract_info(url, download=False)
                    
                    # Check if subtitles are available
                    if info.get('subtitles') or info.get('automatic_captions'):
                        # Download subtitles
                        ydl_opts['writesubtitles'] = True
                        ydl_opts['writeautomaticsub'] = True
                        ydl.download([url])
                        
                        # Look for the subtitle file in the temp directory
                        for file in os.listdir(temp_dir):
                            if file.endswith('.en.vtt'):
                                with open(os.path.join(temp_dir, file), 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    # Clean up the VTT content
                                    lines = []
                                    for line in content.split('\n'):
                                        if not any(x in line.lower() for x in ['webvtt', '-->', '<c>', '</c>', ':', 'align', 'position']):
                                            if line.strip():
                                                lines.append(line.strip())
                                    return ' '.join(lines)
                    
                    return None
                except Exception as e:
                    print(f"yt-dlp error: {str(e)}")
                    return None
    except Exception as e:
        print(f"Error in get_transcript_ytdlp: {str(e)}")
        return None

def get_transcript_api(video_id):
    """Get transcript using youtube_transcript_api."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        return ' '.join([t['text'] for t in transcript])
    except Exception as e:
        print(f"API error: {str(e)}")
        return None

def get_transcript(video_id):
    """Try multiple methods to get the transcript."""
    # Add delay to respect rate limits
    time.sleep(1)
    
    # Try yt-dlp first (more reliable)
    transcript = get_transcript_ytdlp(video_id)
    if transcript:
        return transcript
    
    # Try youtube_transcript_api as fallback
    transcript = get_transcript_api(video_id)
    if transcript:
        return transcript
    
    return "Error: Unable to fetch transcript. This could be due to:\n1. No captions available\n2. Video is private or age-restricted\n3. Try again in a few minutes"

def format_prompt(transcript, style):
    """Formats the prompt for Gemini."""
    prompt_prefix = """Generate structured lecture notes from the following transcript:

- Use plain text formatting (no markdown, no special characters)
- Create clear sections with plain text headings
- Use simple bullet points (just a dash or dot)
- Keep the formatting minimal and clean
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
