from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
import google.generativeai as genai
import tempfile
import pdfplumber
from docx import Document

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or 'dev-secret-key'
csrf = CSRFProtect(app)

# Configure Google AI Studio
google_api_key = os.getenv('GOOGLE_AI_STUDIO_API_KEY')
if not google_api_key:
    raise ValueError("Missing GOOGLE_AI_STUDIO_API_KEY in environment variables")
genai.configure(api_key=google_api_key.strip())
model = genai.GenerativeModel('gemini-pro')

# Mock database (replace with real database in production)
users_db = {}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = users_db.get(email)
        if not user or not check_password_hash(user['password'], password):
            return render_template('signin.html', error='Invalid email or password')
        
        session['user'] = email
        return redirect(url_for('dashboard'))
    
    return render_template('signin.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match')
        
        if len(password) < 8:
            return render_template('signup.html', error='Password must be at least 8 characters')
        
        if email in users_db:
            return render_template('signup.html', error='Email already registered')
        
        users_db[email] = {
            'name': name,
            'email': email,
            'password': generate_password_hash(password)
        }
        
        session['user'] = email
        return redirect(url_for('dashboard'))
    
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    
    user = users_db.get(session['user'])
    if not user:
        return redirect(url_for('signin'))
    
    return render_template('dashboard.html', user=user)

@app.route('/generate', methods=['POST'])
def generate_cover_letter():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        job_title = request.form.get('job_title')
        company_name = request.form.get('company_name')
        job_description = request.form.get('job_description')
        resume_file = request.files.get('resume')
        tone = request.form.get('tone', 'professional')
        length = request.form.get('length', 'medium')
        
        # Extract text from resume if provided
        resume_text = ""
        if resume_file:
            temp_path = tempfile.mktemp()
            resume_file.save(temp_path)
            
            if resume_file.filename.lower().endswith('.pdf'):
                with pdfplumber.open(temp_path) as pdf:
                    resume_text = "\n".join([page.extract_text() for page in pdf.pages])
            elif resume_file.filename.lower().endswith(('.doc', '.docx')):
                doc = Document(temp_path)
                resume_text = "\n".join([para.text for para in doc.paragraphs])
            
            os.unlink(temp_path)
        
        # Enhanced prompt for better results
        prompt = f"""
        Generate a {tone} cover letter for the position of {job_title} at {company_name}.
        The job description is: {job_description}
        Here is the applicant's resume information: {resume_text}
        
        Requirements:
        - Address to hiring manager (use "Dear Hiring Manager" if name unknown)
        - First paragraph: Strong opening showing enthusiasm
        - Second paragraph: Highlight 2-3 most relevant qualifications
        - Third paragraph: Show knowledge of company and position fit
        - Closing paragraph: Call to action and thank you
        - Length: {length} (3-4 paragraphs for medium, 2-3 for short, 4-5 for long)
        - Tone: {tone} (options: professional, enthusiastic, creative, formal)
        - Include specific examples from resume when possible
        - Avoid generic phrases like "I'm excited to apply"
        - Use active voice and strong action verbs
        - Format with proper spacing and paragraphs
        """
        
        # Generate with Google AI Studio
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 1000,
                "top_p": 0.9
            },
            safety_settings={
                "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"
            }
        )
        
        cover_letter = response.text
        
        # Log successful generation
        logger.info(f"Generated cover letter for {session['user']} applying to {company_name}")
        
        return jsonify({
            'coverLetter': cover_letter,
            'jobTitle': job_title,
            'companyName': company_name,
            'generatedAt': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error generating cover letter: {str(e)}")
        return jsonify({
            'error': 'Failed to generate cover letter',
            'details': str(e)
        }), 500

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, port=8000)
