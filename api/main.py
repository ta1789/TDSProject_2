import os
import json
import zipfile
import subprocess
import re
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, File, UploadFile
import httpx
import pdfplumber
import pandas as pd
from io import BytesIO
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()
TOKEN = os.getenv("API_PROXY")
git_token = os.getenv("GIT_TOKEN")

# Initialize FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
CHUNK_SIZE = 4096 * 4096
LLM_API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"


def extract_text_from_pdf(pdf_file) -> str:
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def extract_text_from_csv(csv_file) -> str:
    df = pd.read_csv(csv_file)
    return df.to_string()


def extract_text_from_json(json_file) -> str:
    try:
        data = json.load(json_file)
        return json.dumps(data, indent=2)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format.")


def process_zip_file(zip_file) -> str:
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        extracted_text = ""
        for file_name in zip_ref.namelist():
            with zip_ref.open(file_name) as file:
                if file_name.endswith('.pdf'):
                    extracted_text += extract_text_from_pdf(file)
                elif file_name.endswith('.csv'):
                    extracted_text += extract_text_from_csv(file)
                elif file_name.endswith('.json'):
                    extracted_text += extract_text_from_json(file)
        return extracted_text


def get_response(question: str, file_data: Optional[str] = None) -> dict:
    prompt = f"""
    You are an AI assistant that provides an answer for a given question.
    If your answer contains Python code, please provide the complete code block that can be run directly.
    The code should also print the result. In whichever question if it is asked to use any external tool 
    to perform the question return the python code for that question as a solution.If LLM is able to solve 
    the question by its own donot give python code give the final answer instead. In the python code add the 
    code to install all the required libraries using subprocess and add code to prevent showing installed libraries status like requirement already satisfied in the output screen and import it also and add code to prevent 
    ssl certification.Donot give step by step explanation just give the give code. Give it in a format so that the code can be extracted easily.
    For github based questions I want python code to use GitHub API.For GitHub username use ta1789 and Repository name use TDSProject_Test and for token use {git_token}
    For FastAPI based question use uvicorn with ip as 127.0.0.1 and port as 8002 and return the proper url in answer json and for sending any https request to a url handle the ssl certification issue like Disable SSL Verification in the httpx client by setting the verify parameter to False .
    If the code asks for vercel the code should use vercel api.Donot use sys module in subprocess.If in any question it asks to send request to OpenAI send the request to {LLM_API_URL} with the token {TOKEN}.

    **Question**: {question}
    """
    if file_data:
        prompt += f"\n**File Content**:\n{file_data}\n"

    try:
        response = httpx.post(
            LLM_API_URL,
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]},
            verify=False,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=500, detail=f"LLM API error: {str(e)}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid response from LLM API.")


def execute_python_code(answer: str) -> dict:
    result = {}
    code_match = re.search(r'```python(.*?)```', answer, re.DOTALL)
    if code_match:
        clean_code = code_match.group(1).strip()
        with open("../tmp/code.py", 'w') as f:
            f.write(clean_code)
        try:
            proc_result = subprocess.run(
                ["python", "/tmp/code.py"],
                capture_output=True,
                text=True,
                timeout=10
            )
            result["answer"] = proc_result.stdout or "Execution complete."
        except subprocess.CalledProcessError as e:
            result["error"] = e.stderr
        except subprocess.TimeoutExpired:
            result["error"] = "Execution timed out."
    return result


@app.post("/api/")
async def get_answer(
    question: str = Query(..., description="Question"),
    file: Optional[UploadFile] = File(None)
):
    try:
        file_data = None
        if file:
            content = await file.read()
            file_data = process_zip_file(BytesIO(content)) if file.filename.endswith('.zip') else content.decode('utf-8')

        response = get_response(question, file_data)
        answer = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        is_python = "python" in answer.lower()
        return execute_python_code(answer) if is_python else {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
