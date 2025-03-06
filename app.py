
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from database import db, User
from functools import wraps
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from fer import FER
import cv2
import numpy as np
from googleapiclient.discovery import build
import base64
import logging
from typing import Optional, Dict, Any
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_url_path='/static')
CORS(app, resources={r"/*": {"origins": "*"}})

# App Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
os.makedirs('logs', exist_ok=True)
log_file = f'logs/app_{datetime.now().strftime("%Y%m%d")}.log'
file_handler = logging.FileHandler(log_file)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Create tables
with app.app_context():
    db.create_all()

# Initialize models
try:
    tokenizer = AutoTokenizer.from_pretrained("j-hartmann/emotion-english-roberta-large")
    model = AutoModelForSequenceClassification.from_pretrained("j-hartmann/emotion-english-roberta-large")
    emotion_detector = FER(mtcnn=True)
    logger.info("Models initialized successfully")
except Exception as e:
    logger.error(f"Error initializing models: {str(e)}")
    raise

# Emotion mapping
EMOTION_MAPPING = {
    'joy': 'happy',
    'sadness': 'sad',
    'anger': 'angry',
    'love': 'romantic',
    'fear': 'anxious',
    'surprise': 'excited',
    'neutral': 'neutral'
}

# Load Spotify dataset
try:
    spotify_df = pd.read_csv(r"C:\Users\navya\OneDrive\Documents\End-to-End_Music_Recommender_Chatbot[1]\End-to-End Music Recommender Chatbot\data\data.csv")
    logger.info("Spotify dataset loaded successfully")
except Exception as e:
    logger.error(f"Error loading Spotify dataset: {str(e)}")
    raise

# YouTube API setup
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def check_video_availability(video_id: str) -> bool:
    try:
        request = youtube.videos().list(
            part="status,contentDetails",
            id=video_id
        )
        response = request.execute()
        
        if not response['items']:
            logger.warning(f"Video {video_id} not found")
            return False
            
        video_status = response['items'][0]['status']
        content_details = response['items'][0]['contentDetails']
        is_embeddable = video_status.get('embeddable', False)
        is_public = video_status.get('privacyStatus') == 'public'
        region_restrictions = content_details.get('regionRestriction', {}).get('blocked', [])
        
        # Check if video is playable and not restricted
        return (is_embeddable and 
                is_public and 
                'US' not in region_restrictions and  # Adjust based on your target region
                content_details.get('licensedContent', True))
    except Exception as e:
        logger.error(f"Error checking video availability for {video_id}: {str(e)}")
        return False

def get_youtube_audio_id(song_name: str, artist: str) -> Optional[str]:
    try:
        search_query = f"{song_name} {artist} official audio"
        request = youtube.search().list(
            part="id,snippet",
            q=search_query,
            type="video",
            videoCategoryId="10",
            maxResults=10,
            videoEmbeddable="true",  # Added to filter embeddable videos only
            videoSyndicated="true"   # Added to ensure video is available outside YouTube
        )
        response = request.execute()
        
        for item in response['items']:
            video_id = item['id']['videoId']
            if check_video_availability(video_id):
                logger.info(f"Found available YouTube video ID: {video_id} for {song_name} by {artist}")
                return video_id
        
        logger.warning(f"No suitable video found for {song_name} by {artist}")
        return None
    except Exception as e:
        logger.error(f"Error getting YouTube audio for {song_name} by {artist}: {str(e)}")
        return None

def predict_emotion_from_text(text: str) -> Optional[str]:
    try:
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        
        with torch.no_grad():
            outputs = model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            predicted_label = torch.argmax(predictions, dim=1).item()
            emotion_label = model.config.id2label[predicted_label]
            mapped_emotion = EMOTION_MAPPING.get(emotion_label, 'happy')
            
            confidence = predictions[0][predicted_label].item()
            logger.info(f"Predicted emotion from text: {mapped_emotion} (confidence: {confidence:.2f})")
            return mapped_emotion
            
    except Exception as e:
        logger.error(f"Error predicting emotion from text: {str(e)}")
        return None

def predict_emotion_from_face(frame: np.ndarray) -> Optional[str]:
    try:
        emotions = emotion_detector.detect_emotions(frame)
        if not emotions:
            logger.warning("No faces detected in the frame")
            return None
            
        emotions_dict = emotions[0]['emotions']
        dominant_emotion = max(emotions_dict.items(), key=lambda x: x[1])[0]
        
        emotion_mapping = {
            'happy': 'happy',
            'sad': 'sad',
            'neutral': 'neutral',
            'angry': 'angry',
            'surprise': 'excited',
            'fear': 'anxious',
            'disgust': 'angry'
        }
        
        mapped_emotion = emotion_mapping.get(dominant_emotion, 'happy')
        logger.info(f"Predicted emotion from face: {mapped_emotion}")
        return mapped_emotion
        
    except Exception as e:
        logger.error(f"Error predicting emotion from face: {str(e)}")
        return None

def get_song_recommendation(emotion: str) -> Dict[str, Any]:
    try:
        emotion_features = {
            "happy": {"valence": (0.6, 1.0), "energy": (0.6, 1.0)},
            "sad": {"valence": (0.0, 0.4), "energy": (0.0, 0.5)},
            "neutral": {"valence": (0.4, 0.8), "energy": (0.3, 0.6)},
            "angry": {"valence": (0.0, 0.4), "energy": (0.7, 1.0)},
            "excited": {"valence": (0.7, 1.0), "energy": (0.8, 1.0)},
            "anxious": {"valence": (0.0, 0.3), "energy": (0.5, 0.8)}
        }

        features = emotion_features.get(emotion, emotion_features["happy"])
        filter_conditions = [
            f"{feature} >= {min_val} and {feature} <= {max_val}"
            for feature, (min_val, max_val) in features.items()
            if feature in spotify_df.columns
        ]

        filter_query = " and ".join(filter_conditions)
        matching_songs = spotify_df.query(filter_query) if filter_conditions else spotify_df

        recommended_songs = []
        attempts = 0
        max_attempts = 30  # Increased attempts to ensure we get enough playable songs

        while len(recommended_songs) < 10 and attempts < max_attempts and not matching_songs.empty:
            selected_song = matching_songs.sample(1).iloc[0]
            artist_name = eval(selected_song['artists'])[0] if isinstance(selected_song['artists'], str) else selected_song['artists']
            youtube_id = get_youtube_audio_id(selected_song['name'], artist_name)
            
            if youtube_id:
                recommended_songs.append({
                    'name': str(selected_song['name']),
                    'artist': artist_name,
                    'youtube_id': youtube_id
                })
            matching_songs = matching_songs.drop(selected_song.name)
            attempts += 1
        
        logger.info(f"Recommended {len(recommended_songs)} songs for {emotion}")
        return recommended_songs if recommended_songs else None
    except Exception as e:
        logger.error(f"Error getting song recommendation: {str(e)}")
        return None

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/predict_emotion', methods=['POST'])
@login_required
def predict_emotion():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        emotion = None
        if 'text' in data:
            emotion = predict_emotion_from_text(data['text'])
        elif 'image' in data:
            image_data = base64.b64decode(data['image'].split(',')[1])
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            emotion = predict_emotion_from_face(frame)
        else:
            return jsonify({'error': 'No text or image data provided'}), 400

        if not emotion:
            return jsonify({'error': 'Could not detect emotion'}), 400

        recommended_songs = get_song_recommendation(emotion)
        if not recommended_songs:
            return jsonify({'error': 'Could not find song recommendations'}), 404

        response_data = {
            'emotion': emotion,
            'songs': recommended_songs
        }

        logger.info(f"Successfully generated recommendation: {response_data}")
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error in predict_emotion: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    db.session.rollback()
    logger.error(f"Internal server error: {str(error)}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)