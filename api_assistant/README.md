# AG Extension Q&A API

FastAPI backend that connects to an OpenAI Assistant with Vector Store for question answering based on AG Extension fact sheets.

## Local Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file with your credentials:
```
OPENAI_API_KEY=your_actual_api_key
ASSISTANT_ID=asst_IlflAyLDYVWCfSSJpMZ7ZgEO
```

3. Run locally:
```bash
uvicorn main:app --reload
```

Visit `http://localhost:8000` to see the API running.

## API Endpoints

- `GET /` - Root endpoint with API info
- `GET /health` - Health check
- `POST /ask` - Ask a question
  - Body: `{"message": "your question here"}`
  - Response: `{"response": "assistant answer", "thread_id": "thread_xxx"}`

## Test the API

```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the main topic?"}'
```

## Deploy to Render

1. Push this code to GitHub
2. Create a new Web Service on Render
3. Connect your GitHub repo
4. Add environment variables in Render dashboard:
   - `OPENAI_API_KEY`
   - `ASSISTANT_ID`
5. Deploy!

Render will automatically detect the Python project and install dependencies.
