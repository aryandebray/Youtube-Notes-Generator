from flask import Flask, request, jsonify, render_template
import re
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import os

# Configure Gemini API
api_key = os.getenv('GEMINI_API_KEY', "AIzaSyAL-dytEp5xgyB3TpwvXijz4xXXoBNjXTQ")  # Use environment variable in production
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

app = Flask(__name__)

def extract_video_id(youtube_url):
    """Extracts the YouTube video ID."""
    match = re.search(r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/)([a-zA-Z0-9_-]{11})", youtube_url)
    return match.group(1) if match else None

def get_transcript(video_id):
    """Fetches the YouTube transcript."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t['text'] for t in transcript])
    except Exception as e:
        return f"Error fetching transcript: {e}"

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
    if "Error" in transcript:
        return jsonify({"error": transcript}), 400
    
    notes = generate_notes(transcript, style)
    if "Error" in notes:
        return jsonify({"error": notes}), 500
    
    return jsonify({"notes": notes})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
