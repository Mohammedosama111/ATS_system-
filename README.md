# ATS Agent (Streamlit + LangChain)

An AI-powered Applicant Tracking System that ingests resumes and job descriptions, stores data in a database, and uses multiple LLMs (OpenAI GPT-4o-mini, Anthropic Claude 3.5, Google Gemini 2.5 Pro) via LangChain to intelligently classify resumes as approved or rejected with detailed reasoning.

## Features
- **Multi-Provider LLM Support**: Switch between OpenAI, Anthropic (Claude), and Google (Gemini 2.5 Pro) in real-time
- **Streamlit UI**: Clean interface for uploading resumes, entering job details, and viewing results
- **Smart Resume Parsing**: Parse PDF and DOCX resumes with fallback mechanisms
- **Database Storage**: SQLite (default) or PostgreSQL/MySQL via SQLAlchemy ORM
- **Detailed Results**: View approved and rejected resumes with resume filenames and AI-generated rationales
- **JSON Output Parsing**: Deterministic structured output with error handling and guardrails
- **Temperature Control**: Adjust LLM creativity via sidebar slider
- **Separate Lists**: Clear separation of approved vs rejected candidates with reasoning

## Project Structure
```
ATS agent/
├── app.py                      # Streamlit app entry point
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in git)
├── ats.db                      # SQLite database (not in git)
├── config/
│   └── settings.py            # Configuration and API key management
├── database/
│   ├── db_manager.py          # Database session and engine
│   └── models.py              # SQLAlchemy ORM models (Resume, Job, Decision)
├── llm/
│   ├── llm_handler.py         # LLM provider factory and review logic
│   └── prompts.py             # LangChain prompt templates
└── utils/
    └── resume_parser.py       # PDF/DOCX parsing utilities
```

## Tech Stack
- **Frontend**: Streamlit 1.38.0
- **LLM Orchestration**: LangChain 0.3.x with official provider adapters
- **Database**: SQLAlchemy 2.0.35 with SQLite default
- **AI Models**:
  - OpenAI: gpt-4o-mini via `langchain-openai`
  - Anthropic: claude-3-5-sonnet-20240620 via `langchain-anthropic`
  - Google: gemini-2.5-pro via `langchain-google-genai`
- **Parsing**: PyPDF2, pdfminer.six, python-docx

## Setup

### Prerequisites
- Python 3.13+ (tested on Python 3.13, Windows 11)
- API keys from OpenAI, Anthropic, and/or Google AI

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Mohammedosama111/ATS_system-.git
   cd "ATS agent"
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Mac/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   DATABASE_URL=sqlite:///./ats.db
   DEFAULT_LLM_PROVIDER=openai
   OPENAI_API_KEY=your_openai_key_here
   ANTHROPIC_API_KEY=your_anthropic_key_here
   GOOGLE_API_KEY=your_google_api_key_here
   ```

5. **Run the application**
   ```bash
   streamlit run app.py
   # or using venv Python directly
   .venv\Scripts\python -m streamlit run app.py
   ```

6. **Open in browser**
   Navigate to `http://localhost:8501`

## Usage

1. **Select LLM Provider**: Choose OpenAI, Anthropic, or Google from the sidebar
2. **Adjust Temperature**: Control output creativity (0.0 = deterministic, 1.0 = creative)
3. **Enter Job Details**:
   - Job Title
   - Job Description (paste full JD)
   - Extra HR Instructions (optional screening criteria)
4. **Upload Resumes**: Select multiple PDF or DOCX files
5. **Run Screening**: Click the button and wait for AI analysis
6. **Review Results**:
   - **Approved Resumes**: Shows filename, ID, and detailed reasoning
   - **Rejected Resumes**: Shows filename, ID, and why they didn't match
   - **Raw Decisions**: JSON export available in expander

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `sqlite:///./ats.db` | SQLAlchemy database connection string |
| `DEFAULT_LLM_PROVIDER` | No | `openai` | One of: `openai`, `anthropic`, `google` |
| `OPENAI_API_KEY` | Yes* | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | Yes* | - | Anthropic API key |
| `GOOGLE_API_KEY` | Yes* | - | Google AI API key (Gemini) |

*At least one API key is required for the selected provider

## Database Schema

- **Resume**: Stores uploaded resume filename and parsed text content
- **Job**: Stores job title, description, and HR instructions
- **Decision**: Links resumes to jobs with AI decision (approved/rejected) and rationale

## Development Notes

### Python 3.13 Compatibility
- Uses binary wheels for numpy/pandas (no source builds on Windows)
- LangChain 0.3.x required for Python 3.13 support
- All dependencies tested on Windows 11 with Python 3.13

### Model Selection
- **Gemini**: Uses `gemini-2.5-pro` for advanced reasoning
- **OpenAI**: Uses `gpt-4o-mini` for cost-effective screening
- **Claude**: Uses `claude-3-5-sonnet-20240620` for balanced performance

### Future Enhancements
- CSV export of screening results
- Historical screening view (show past jobs and decisions)
- Bulk resume download/upload
- Custom prompt templates per job
- Multi-language resume support
- Advanced parsing with `unstructured` or `textract`

## Troubleshooting

**Streamlit not found**: Use `.venv\Scripts\python -m streamlit run app.py`

**API Key errors**: Verify `.env` file exists and contains valid keys

**Model not found (404)**: Some Gemini models require specific API versions. Try:
- `gemini-2.0-pro`
- `gemini-1.5-pro-latest`
- `gemini-2.0-flash`

**Parsing errors**: Ensure PDFs are text-based (not scanned images). Use OCR preprocessing if needed.

## License
MIT License - Feel free to use and modify

## Contributing
Pull requests welcome! Please ensure code follows the existing structure and includes tests for new features.
