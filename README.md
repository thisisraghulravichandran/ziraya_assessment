# ziraya_assessment

## Overview

**ziraya_assessment** is a Flask-based web application for document compliance checking and modification using AI. Users can upload documents, receive compliance feedback, and get AI-powered suggestions or corrections.

## Features

- Upload and process documents
- AI-powered compliance checking and grammar suggestions
- Download modified documents
- User-friendly web interface

## Project Structure

```
ziraya_assessment/
├── app.py                # Main Flask application
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (not committed)
├── static/               # Static files (JS, CSS)
│   ├── script.js
│   └── style.css
├── templates/            # HTML templates
│   └── index.html
├── processed/            # Processed and output files
├── uploads/              # Uploaded files
└── README.md             # Project documentation
```

## Setup Instructions

1. **Clone the repository:**

   ```sh
   git clone <repo-url>
   cd ziraya_assessment
   ```

2. **Create and activate a virtual environment (recommended):**

   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**

   ```sh
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**

   - Create a `.env` file in the project root with the following (example):
     ```env
     AI_API_KEY=your-api-key-here
     AI_API_URL=''
     AI_MODEL=''
     ```

5. **Run the application:**
   ```sh
   python3 app.py
   ```
   The app will be available at [http://localhost:5001](http://localhost:5001) (or the port you specify).

## Usage

1. Open your browser and go to [http://localhost:5001](http://localhost:5001)
2. Upload a document (e.g., cover letter)
3. Review compliance feedback and AI suggestions
4. Download the modified document if needed

## Environment Variables

| Variable           | Description                                   |
| ------------------ | --------------------------------------------- |
| AI_API_KEY         | API key for the AI provider                   |
| AI_API_URL         | Endpoint for the AI API                       |
| AI_MODEL           | Model name for AI requests                    |

## License

This project is for assessment and demonstration purposes.

## Contact

For questions or support, contact: [thisisraghulravichandran@gmail.com](mailto:thisisraghulravichandran@gmail.com)
