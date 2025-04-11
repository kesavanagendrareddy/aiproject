from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import google.generativeai as genai
import os
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime
import PyPDF2
from docx import Document
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'uploads/'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize genAI
genai.configure(api_key="AIzaSyDc4OY3rcVFXj5VJEujqU7TxfyQub5wVWA", transport='rest')

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
        
        if user and user[2] == password:
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
                     (username, password))
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
    
    job_title = request.form.get('job_title')
    company = request.form.get('company')
    job_description = request.form.get('job_description')
    resume_text = ""
    
    if 'resume_file' in request.files:
        resume_file = request.files['resume_file']
        if resume_file.filename != '':
            filename = secure_filename(resume_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume_file.save(filepath)
            
            if filename.endswith('.pdf'):
                with open(filepath, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    resume_text = "\n".join([page.extract_text() for page in reader.pages])
            elif filename.endswith('.docx'):
                doc = Document(filepath)
                resume_text = "\n".join([para.text for para in doc.paragraphs])
            else:
                with open(filepath, 'r') as f:
                    resume_text = f.read()
    else:
        resume_text = request.form.get('resume_text', "")
        if not resume_text:
            return jsonify({'error': 'Please provide either a resume file or text'}), 400
    
    prompt = f"""
    Analyze this resume and generate a professional cover letter for {job_title} position at {company}.
    Job requirements: {job_description}
    
    Instructions:
    1. Use clean, professional formatting without markdown symbols (#, *, -)
    2. Structure as a proper business letter with:
       - Sender's contact info
       - Date
       - Recipient details
       - Salutation
       - 3-4 paragraph body
       - Closing
    3. Focus on skills matching these job requirements
    4. Remove any analysis notes or section headers
    5. Use proper punctuation and formatting
    
    Resume content:
    {resume_text}
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 1000,
            }
        )
        
        cover_letter = response.text
        # Remove markdown symbols and clean up formatting
        cover_letter = (cover_letter.replace('**', '')
                       .replace('*', '')
                       .replace('#', '')
                       .replace('## ', '')
                       .replace('### ', ''))
        # Remove any analysis sections if present
        if 'Resume Analysis:' in cover_letter:
            cover_letter = cover_letter.split('Cover Letter')[1] if 'Cover Letter' in cover_letter else cover_letter
        
        # Generate PDF version with Unicode support
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font('DejaVu', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', uni=True)
        pdf.set_font('DejaVu', size=12)
        pdf.multi_cell(0, 10, cover_letter)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'cover_letter.pdf')
        pdf.output(pdf_path)
        
        return jsonify({
            'cover_letter': cover_letter,
            'pdf_url': f'/download/cover_letter.pdf'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=8000)