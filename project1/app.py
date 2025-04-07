from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import google.generativeai as genai
import os
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'uploads/'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize genAI
genai.api_key = "AIzaSyDc4OY3rcVFXj5VJEujqU7TxfyQub5wVWA"

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE,
                 password TEXT,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        
        if user and user[2] == password:  # In production, use proper password hashing
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
    
    return render_template('signin.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                     (username, password))  # In production, hash the password
            conn.commit()
            conn.close()
            return redirect(url_for('signin'))
        except sqlite3.IntegrityError:
            return "Username already exists", 400
    
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    return render_template('dashboard.html')

@app.route('/generate', methods=['POST'])
def generate_cover_letter():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    job_title = data.get('job_title')
    company = data.get('company')
    job_description = data.get('job_description')
    resume_text = data.get('resume_text')
    
    prompt = f"""
    Write a professional, human-sounding cover letter for the position of {job_title} at {company}.
    The job description is: {job_description}
    Here is the applicant's resume information: {resume_text}
    
    Requirements:
    - Address the hiring manager professionally
    - Highlight relevant skills from the resume that match the job description
    - Keep it concise (3-4 paragraphs)
    - Use natural, conversational but professional tone
    - Avoid generic phrases, make it specific to the role
    - Format as a proper business letter
    """
    
    try:
        genai.configure(api_key="AIzaSyDc4OY3rcVFXj5VJEujqU7TxfyQub5wVWA")
        
        response = genai.GenerativeModel('gemini-1.5-pro').generate_content(
            f"Act as a professional career advisor. {prompt}",
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 1000,
            }
        )
        
        cover_letter = response.text
        return jsonify({'cover_letter': cover_letter})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8000)