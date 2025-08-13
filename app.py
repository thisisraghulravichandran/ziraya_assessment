# app.py
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import PyPDF2
from docx import Document
import json
import logging
from functools import wraps

from dotenv import load_dotenv

load_dotenv()

# Read AI config from .env
AI_API_KEY = os.getenv('AI_API_KEY', 'your-api-key-here')
AI_API_URL = os.getenv('AI_API_URL', 'https://openrouter.ai/api/v1/chat/completions')
AI_MODEL = os.getenv('AI_MODEL', 'deepseek/deepseek-chat-v3-0324:free')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'processed'

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}

# English guidelines for compliance checking
ENGLISH_GUIDELINES = """
1. Grammar Rules:
   - Use proper subject-verb agreement
   - Correct use of tenses
   - Proper punctuation and capitalization
   - Avoid run-on sentences
   - Do not flag email addresses for capitalization or grammar issues.

2. Sentence Structure:
   - Use clear and concise sentences
   - Avoid overly complex sentence structures
   - Maintain proper sentence flow
   - Use active voice when possible

3. Clarity and Style:
   - Use simple and clear language
   - Avoid unnecessary jargon
   - Maintain consistent tone
   - Use proper paragraph structure

4. Writing Rules:
   - Use proper spelling
   - Maintain consistent formatting
   - Use appropriate transitions
   - Ensure logical flow of ideas
"""

class DocumentProcessor:
    """Handles document processing and text extraction"""
    
    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    @staticmethod
    def extract_text_from_pdf(file_path):
        """Extract text from PDF file"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    @staticmethod
    def extract_text_from_docx(file_path):
        """Extract text from DOCX file"""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            raise Exception(f"Failed to extract text from DOCX: {str(e)}")
    
    @staticmethod
    def extract_text(file_path, filename):
        """Extract text based on file extension"""
        extension = filename.rsplit('.', 1)[1].lower()
        
        if extension == 'pdf':
            return DocumentProcessor.extract_text_from_pdf(file_path)
        elif extension in ['docx', 'doc']:
            return DocumentProcessor.extract_text_from_docx(file_path)
        else:
            raise Exception(f"Unsupported file format: {extension}")

class AIAgent:
    """AI agent for document compliance checking and modification"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def _make_api_request(self, messages, max_tokens=2000):
        """Make request to OpenRouter API"""
        try:
            payload = {
                "model": AI_MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3
            }
            
            response = requests.post(AI_API_URL, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise Exception(f"AI service unavailable: {str(e)}")
        except KeyError as e:
            logger.error(f"Unexpected API response format: {e}")
            raise Exception("Invalid response from AI service")
    
    def check_compliance(self, document_text):
        """Check document compliance against English guidelines"""
        prompt = f"""
        You are an expert English language compliance checker. Analyze the following document text against these guidelines:

        {ENGLISH_GUIDELINES}

        Document Text:
        {document_text[:3000]}...

        Please provide a detailed compliance report in the following JSON format:
        {{
            "overall_compliance": "COMPLIANT" or "NON_COMPLIANT",
            "compliance_score": <score out of 100>,
            "violations": [
                {{
                    "category": "<Grammar/Structure/Clarity/Writing>",
                    "issue": "<description of the issue>",
                    "location": "<approximate location in text>",
                    "severity": "<High/Medium/Low>"
                }}
            ],
            "suggestions": [
                "<general improvement suggestions>"
            ],
            "summary": "<overall summary of compliance status>"
        }}

        Focus on identifying specific violations and provide actionable feedback.
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = self._make_api_request(messages)
        
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                # Fallback if JSON parsing fails
                return {
                    "overall_compliance": "NON_COMPLIANT",
                    "compliance_score": 70,
                    "violations": [{"category": "General", "issue": "Analysis completed", "location": "Document", "severity": "Medium"}],
                    "suggestions": ["Review document for compliance"],
                    "summary": response
                }
        except json.JSONDecodeError:
            logger.error("Failed to parse AI response as JSON")
            return {
                "overall_compliance": "NON_COMPLIANT",
                "compliance_score": 70,
                "violations": [],
                "suggestions": [],
                "summary": response
            }
    
    def modify_document(self, document_text, compliance_report):
        """Modify document to comply with guidelines"""
        violations_summary = "\n".join([f"- {v['issue']}" for v in compliance_report.get('violations', [])])
        
        prompt = f"""
        You are an expert English editor. Please rewrite the following document to comply with English writing guidelines.

        Original Guidelines Violations:
        {violations_summary}

        Original Document:
        {document_text}

        Please provide a corrected version that addresses all compliance issues while maintaining the original meaning and intent. 
        Focus on:
        - Fixing grammar errors
        - Improving sentence structure
        - Enhancing clarity
        - Correcting spelling and punctuation
        - Maintaining logical flow

        Return only the corrected document text without additional commentary.
        """
        
        messages = [{"role": "user", "content": prompt}]
        return self._make_api_request(messages, max_tokens=3000)

# Initialize AI agent
ai_agent = AIAgent(AI_API_KEY)

def handle_errors(f):
    """Decorator for error handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {e}")
            return jsonify({'error': str(e)}), 500
    return decorated_function

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
@handle_errors
def upload_document():
    """Upload and process document"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not DocumentProcessor.allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Please upload PDF or DOCX files.'}), 400
    
    # Save uploaded file
    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
    file.save(file_path)
    
    try:
        # Extract text from document
        document_text = DocumentProcessor.extract_text(file_path, filename)
        
        if not document_text.strip():
            return jsonify({'error': 'No text could be extracted from the document'}), 400
        
        # Check compliance
        compliance_report = ai_agent.check_compliance(document_text)
        
        # Store session data
        session_data = {
            'file_id': file_id,
            'original_filename': filename,
            'document_text': document_text,
            'compliance_report': compliance_report,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save session data
        session_file = os.path.join(app.config['PROCESSED_FOLDER'], f"{file_id}_session.json")
        with open(session_file, 'w') as f:
            json.dump(session_data, f)
        
        return jsonify({
            'file_id': file_id,
            'filename': filename,
            'compliance_report': compliance_report,
            'message': 'Document processed successfully'
        })
        
    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)

@app.route('/modify/<file_id>', methods=['POST'])
@handle_errors
def modify_document(file_id):
    """Modify document for compliance"""
    session_file = os.path.join(app.config['PROCESSED_FOLDER'], f"{file_id}_session.json")
    
    if not os.path.exists(session_file):
        return jsonify({'error': 'Session not found'}), 404
    
    # Load session data
    with open(session_file, 'r') as f:
        session_data = json.load(f)
    
    document_text = session_data['document_text']
    compliance_report = session_data['compliance_report']
    
    # Modify document using AI
    modified_text = ai_agent.modify_document(document_text, compliance_report)
    
    # Save modified document
    modified_filename = f"modified_{session_data['original_filename'].rsplit('.', 1)[0]}.txt"
    modified_file_path = os.path.join(app.config['PROCESSED_FOLDER'], f"{file_id}_{modified_filename}")
    
    with open(modified_file_path, 'w', encoding='utf-8') as f:
        f.write(modified_text)
    
    # Update session data
    session_data['modified_text'] = modified_text
    session_data['modified_filename'] = modified_filename
    
    with open(session_file, 'w') as f:
        json.dump(session_data, f)
    
    return jsonify({
        'file_id': file_id,
        'modified_filename': modified_filename,
        'message': 'Document modified successfully',
        'preview': modified_text[:500] + '...' if len(modified_text) > 500 else modified_text
    })

@app.route('/download/<file_id>')
@handle_errors
def download_modified(file_id):
    """Download modified document"""
    session_file = os.path.join(app.config['PROCESSED_FOLDER'], f"{file_id}_session.json")
    
    if not os.path.exists(session_file):
        return jsonify({'error': 'Session not found'}), 404
    
    with open(session_file, 'r') as f:
        session_data = json.load(f)
    
    if 'modified_filename' not in session_data:
        return jsonify({'error': 'Modified document not found'}), 404
    
    modified_file_path = os.path.join(app.config['PROCESSED_FOLDER'], f"{file_id}_{session_data['modified_filename']}")
    
    if not os.path.exists(modified_file_path):
        return jsonify({'error': 'Modified file not found'}), 404
    
    return send_file(modified_file_path, as_attachment=True, download_name=session_data['modified_filename'])

@app.route('/status/<file_id>')
@handle_errors
def get_status(file_id):
    """Get processing status"""
    session_file = os.path.join(app.config['PROCESSED_FOLDER'], f"{file_id}_session.json")
    
    if not os.path.exists(session_file):
        return jsonify({'error': 'Session not found'}), 404
    
    with open(session_file, 'r') as f:
        session_data = json.load(f)
    
    return jsonify({
        'file_id': file_id,
        'original_filename': session_data['original_filename'],
        'compliance_report': session_data['compliance_report'],
        'has_modified': 'modified_text' in session_data,
        'timestamp': session_data['timestamp']
    })

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)