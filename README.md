# Implementing-Chatbot-Based-Music-Recommendation-using-Emotions-
Implementing Chatbot-Based Music Recommendation using Emotions is a project where it recommends the songs based on the user emotions and the emotions can be taken from humans through text and capture the image and recommends the songs.

The use of chatbots has grown significantly in recent years as organizations strive to improve customer engagement. One area where chatbots are gaining attention is music recommendation. Chatbot-based music recommenders utilize AI technologies to offer personalized song recommendations through conversational interfaces. These systems provide a unique, engaging experience by interpreting user emotions and preferences through natural language interactions. This project focuses on developing a personalized chatbot music recommender system using Natural Language Processing (NLP) techniques. The chatbot interacts with users, identifies their emotional state, and suggests relevant songs to match their mood, making music discovery more intuitive. The solution will integrate a web-based interface, allowing users to access music recommendations seamlessly. The outcome is expected to improve user engagement and satisfaction by delivering real-time, emotionally aligned music recommendations through an intelligent, user-friendly chatbot system.

# Steps to install 
### 1. Clone the Repository
bash
git clone <repository-url>
cd music_recommender

### 2. Environment Setup
bash
# Create and activate environment
conda create -n music_recommender python=3.9
conda activate music_recommender

# Install dependencies
pip install -r requirements.txt


### 3. Dependencies
flask==2.0.1
flask-cors==3.0.10
flask-sqlalchemy==3.0.3
pandas==1.4.4
transformers==4.21.0
torch==1.9.0
fer==22.4.0
opencv-python==4.6.0.66
numpy==1.21.5
google-api-python-client==2.86.0
python-dotenv==1.0.0
werkzeug==2.3.4

## Configuration
### 1. Environment Variables
Create .env file in project root:
.env

YOUTUBE_API_KEY=your_youtube_api_key_here


### 2. Database Setup
Database configuration is automatic. The database will be created at first run.

## Running the Application
### Local Development
bash
# Activate environment
conda activate music_recommender

## Install dependencies
1- conda install -y -c conda-forge flask=2.0.1 flask-cors=3.0.10 flask-sqlalchemy=3.0.3 pandas=1.4.4 numpy=1.21.5 python-dotenv=1.0.0 werkzeug=2.3.4
2- pip install transformers==4.21.0 torch==1.9.0 fer==22.4.0 opencv-python==4.6.0.66 google-api-python-client==2.86.0

# Run application
python app.py

# Access at http://localhost:5000
