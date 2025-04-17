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
        # Ensure text is properly encoded
        resume_text = resume_text.encode('utf-8').decode('utf-8')
    
    company_location = request.form.get('company_location', "")
    interview_date = request.form.get('interview_date', "")
    
    location_info = f" in {company_location}" if company_location else ""
    interview_info = f"\nInterview scheduled for: {interview_date}" if interview_date else ""
    
    prompt = f"""
    Generate a highly personalized cover letter for {job_title} position at {company}{location_info} using this resume.{interview_info}
    Follow these guidelines strictly:
    
    1. Business Letter Format:
    - Sender's full contact info (from resume)
    - Current date
    - Hiring manager/company address
    - Professional salutation
    
    2. Content Requirements:
    First Paragraph:
    - Mention exact position and company
    - Highlight 2-3 most relevant skills from resume
    - Show enthusiasm for the role
    
    Middle Paragraph(s):
    - Match 3-5 specific requirements from: {job_description}
    - Provide concrete examples from resume
    - Use metrics/achievements when possible
    
    Closing Paragraph:
    - Reiterate interest
    - Mention availability for interview
    - Professional sign-off
    
    3. Style Guidelines:
    - Tone: Professional yet enthusiastic
    - Length: 3-4 paragraphs
    - No generic phrases - all content must be resume-specific
    - Vary sentence structure between requests
    
    Resume Content:
    {resume_text}
    
    Job Description:
    {job_description}
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.9,  # Increased for more creativity
                "max_output_tokens": 1200,
                "top_p": 0.95,      # For more diverse outputs
                "top_k": 40         # Wider selection of tokens
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
        app.logger.error(f"Error generating cover letter: {str(e)}")
        return jsonify({'error': 'Failed to generate cover letter. Please try again.'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=8000)