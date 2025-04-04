# AI Cover Letter Generator

A web application that generates personalized cover letters using AI.

## Features

- User authentication (Sign Up/Sign In)
- Cover letter generation from job details
- Resume upload and text extraction (PDF/DOCX)
- Download generated cover letters as PDF

## Setup

1. Clone the repository
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate    # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file and add your:
   - `SECRET_KEY` (any random string)
   - `OPENAI_API_KEY` (from platform.openai.com)

5. Run the application:
   ```bash
   python app.py
   ```
6. Access the application at `http://localhost:8000`

## Usage

1. Sign up for an account
2. On the dashboard:
   - Enter job details (title, company, description)
   - Optionally upload your resume
   - Click "Generate Cover Letter"
3. View and download your personalized cover letter

## Future Improvements

- Add database persistence (SQLAlchemy)
- Implement PDF download functionality
- Add cover letter history and editing
- Include multiple template options
- Add social login (Google, GitHub)

## Technologies Used

- Frontend: HTML5, Tailwind CSS, JavaScript
- Backend: Python, Flask
- AI: OpenAI GPT-3.5/4
- File Processing: pdfplumber, python-docx