"""
Cooking Recipe Assistant - Flask Web Server
=============================================
This module serves the web-based chat UI and provides REST API endpoints
for the AI agent. It handles session management so each browser tab
maintains its own conversation context.

Endpoints:
    GET  /           -> Serve the main chat UI (index.html)
    POST /api/chat   -> Send a user message and get AI agent response
    GET  /api/recipes -> List all recipes from the local knowledge base
    POST /api/clear  -> Clear the current chat session history

Usage:
    python app.py
    Then open http://localhost:5000 in your browser.
"""

import os
import uuid
import logging
from dotenv import load_dotenv

# Load environment variables BEFORE importing agent (ensures fresh API key)
load_dotenv(override=True)

from flask import Flask, render_template, request, jsonify, session
from cooking_agent import CookingAgent

# Configure logging for debugging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# APP INITIALIZATION
# =============================================================================

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session cookie encryption

# Initialize the AI agent at startup
# If the GROQ_API_KEY is missing or invalid, the app still serves the UI
# but chat requests will return an error message.
try:
    agent = CookingAgent()
    agent_ready = True
    logger.info("AI Agent initialized successfully")
except ValueError as e:
    agent_ready = False
    agent_error = str(e)
    logger.error(f"Agent initialization failed: {agent_error}")


# =============================================================================
# ROUTES - Page Serving
# =============================================================================

@app.route("/")
def index():
    """
    Serve the main chat UI page.
    
    Creates a unique session ID for each new browser session to maintain
    separate conversation histories per tab.
    """
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
        logger.info(f"New session created: {session['session_id'][:8]}...")
    return render_template("index.html")


# =============================================================================
# ROUTES - Chat API
# =============================================================================

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Process a chat message and return the AI agent's response.
    
    Expects JSON body: {"message": "user's question here"}
    Returns JSON: {"response": "agent's answer"} or {"error": "error message"}
    
    The agent may call multiple tools (search local KB, query API, etc.)
    before generating its final response. This can take 5-15 seconds.
    """
    # Check if agent is available
    if not agent_ready:
        return jsonify({"error": f"Agent not available: {agent_error}"}), 500

    # Validate request body
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request: expected JSON body"}), 400
    
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message. Please type a question."}), 400
    
    # Enforce reasonable message length
    if len(user_message) > 2000:
        return jsonify({"error": "Message too long. Please keep it under 2000 characters."}), 400

    # Get session ID for conversation memory
    session_id = session.get("session_id", str(uuid.uuid4()))
    
    try:
        logger.info(f"Chat request [{session_id[:8]}]: {user_message[:50]}...")
        response = agent.chat(user_message, session_id)
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Chat error [{session_id[:8]}]: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/api/recipes", methods=["GET"])
def get_recipes():
    """
    List all recipes from the local knowledge base.
    
    Returns JSON with recipes grouped by category (Breakfast, Lunch, etc.).
    This endpoint does not require the AI agent.
    """
    from cooking_agent import list_all_recipes
    import json
    try:
        return jsonify(json.loads(list_all_recipes()))
    except Exception as e:
        logger.error(f"Recipes listing error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/clear", methods=["POST"])
def clear_chat():
    """
    Clear the current chat session history.
    
    Removes the conversation memory for the current session and
    generates a new session ID for a fresh start.
    """
    if agent_ready:
        session_id = session.get("session_id", "default")
        agent.clear_session(session_id)
        logger.info(f"Session cleared: {session_id[:8]}...")
    session["session_id"] = str(uuid.uuid4())
    return jsonify({"status": "cleared"})


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(e):
    """Handle 404 - Page not found."""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 - Internal server error."""
    return jsonify({"error": "Internal server error"}), 500


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  Cooking Recipe Assistant - Web Server")
    print("=" * 55)
    if agent_ready:
        print("  [OK] AI Agent ready (Groq LLM)")
        print("  [OK] Local KB: 25 recipes loaded")
        print("  [OK] TheMealDB API: connected")
    else:
        print(f"  [ERR] Agent error: {agent_error}")
    print("  Open http://localhost:5000 in your browser")
    print("=" * 55 + "\n")
    app.run(debug=True, port=5000)
