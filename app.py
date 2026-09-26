"""
Flask backend for the Study Buddy chatbot.

This app exposes:
- GET  /        -> renders the chat UI (templates/index.html)
- POST /chat    -> receives a user message + conversation history,
                   sends it to the Gemini API together with the
                   chatbot's system prompt, and returns the reply.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

from chatbot_config import CHATBOT_NAME, MODEL_NAME, SYSTEM_PROMPT

# Load GEMINI_API_KEY from the .env file.
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Add it to your .env file before "
        "starting the app."
    )

# Create the Gemini client once, at startup.
client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)


@app.route("/")
def index():
    """Render the chat page."""
    return render_template("index.html", chatbot_name=CHATBOT_NAME)


@app.route("/chat", methods=["POST"])
def chat():
    """Handle a single chat turn.

    Expects JSON: { "message": str, "history": [ {role, text}, ... ] }
    Returns JSON: { "reply": str } or { "error": str }
    """
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not user_message:
        return jsonify({"error": "Message cannot be empty."}), 400

    try:
        # Rebuild the conversation so Gemini has context of earlier turns.
        contents = []
        for turn in history:
            role = "model" if turn.get("role") == "bot" else "user"
            text = turn.get("text", "")
            if text:
                contents.append(
                    types.Content(role=role, parts=[types.Part(text=text)])
                )
        contents.append(
            types.Content(role="user", parts=[types.Part(text=user_message)])
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
        )

        reply_text = (response.text or "").strip()
        if not reply_text:
            reply_text = "Sorry, I couldn't generate a response. Please try again."

        return jsonify({"reply": reply_text})

    except Exception as exc:  # noqa: BLE001 - surface a clean error to the UI
        return jsonify({"error": f"Something went wrong: {exc}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
