import subprocess
import json
import re


def safe_json_from_llm(text: str):
    """
    Extracts and safely parses JSON from LLM output.
    """

    # Remove non-printable characters
    text = re.sub(r"[\x00-\x1F\x7F]", "", text)

    # Try direct JSON parse
    try:
        return json.loads(text)
    except:
        pass

    # Extract JSON block
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON found in LLM output")

    json_text = match.group()

    # Fix common LLM JSON issues
    json_text = re.sub(r",\s*}", "}", json_text)
    json_text = re.sub(r",\s*]", "]", json_text)
    json_text = re.sub(r":\s*,", ": null,", json_text)

    return json.loads(json_text)


def generate_mcqs(skill: str):
    """
    Generates 5 MCQs for a given skill using phi3:mini via Ollama
    """

    prompt = f"""
You are an expert technical interviewer.

Generate exactly 5 multiple-choice questions to assess knowledge of the skill: "{skill}".

Rules:
- Each question must have exactly 4 options (A, B, C, D)
- Only ONE option is correct
- Difficulty: beginner to intermediate
- Output MUST be valid JSON in the following format ONLY:

{{
  "skill": "{skill}",
  "questions": [
    {{
      "question": "...",
      "options": {{
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "..."
      }},
      "answer": "A"
    }}
  ]
}}

DO NOT add explanations.
DO NOT add markdown.
DO NOT add extra text.
"""

    result = subprocess.run(
        ["ollama", "run", "gpt-oss:120b-cloud"],
        input=prompt,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="ignore"
    )

    raw_output = result.stdout.strip()

    try:
        return safe_json_from_llm(raw_output)
    except Exception as e:
        # graceful fallback (prevents Streamlit crash)
        return {
            "skill": skill,
            "questions": []
        }
