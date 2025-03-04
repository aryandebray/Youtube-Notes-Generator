from flask import Flask, request, jsonify, render_template
import re
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import os
import time
from functools import wraps

# Configure Gemini API
api_key = os.getenv('GEMINI_API_KEY', "AIzaSyAL-dytEp5xgyB3TpwvXijz4xXXoBNjXTQ")  # Use environment variable in production
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

@rate_limited(1)  # Limit to 1 request per second
def get_transcript(video_id):
    """Fetches the YouTube transcript with rate limiting and better error handling."""
    try:
        # First try to get English transcript
        
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        except:
            # If English not available, try auto-generated transcript
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Join transcript texts with proper spacing and punctuation
        text_parts = []
        for t in transcript:
            text = t['text'].strip()
            if text:
                # Add period if the text doesn't end with punctuation
                if not text[-1] in '.!?':
                    text += '.'
                text_parts.append(text)
        
        return ' '.join(text_parts)
    except Exception as e:
        error_msg = str(e)
        if "Too Many Requests" in error_msg:
            return "Error: YouTube is rate limiting requests. Please try again in a few minutes."
        elif "TranscriptsDisabled" in error_msg:
            return "Error: This video does not have captions/transcripts enabled."
        elif "NoTranscriptFound" in error_msg:
            return "Error: No transcript found for this video. It might not have captions available."
        else:
            return f"Error fetching transcript: {error_msg}"

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
    if "Error" in transcript:
        return jsonify({"error": transcript}), 400
    
    notes = generate_notes(transcript, style)
    if "Error" in notes:
        return jsonify({"error": notes}), 500
    
    return jsonify({"notes": notes})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
