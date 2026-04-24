# Cooking Recipe Assistant - AI Agent

An AI-powered cooking recipe assistant that suggests recipes based on available ingredients and provides step-by-step cooking instructions. Built as an **AI Agent** (not a simple chatbot) using Groq LLM with autonomous tool-calling and a **dual knowledge base** (Local JSON + TheMealDB API).

---

## Features

- **AI Agent with Tool-Calling** - Uses Groq LLM (llama-3.3-70b) with 5 autonomous tools
- **Dual Knowledge Base** - 25 curated local recipes + 300+ online recipes via TheMealDB API
- **Ingredient-Based Search** - Fuzzy matching to find recipes from what you have
- **Step-by-Step Instructions** - Detailed cooking steps with ingredient quantities
- **Dietary Filters** - Vegetarian, vegan, and gluten-free tags
- **Web UI** - Premium browser-based chat interface (Flask + HTML/CSS/JS)
- **Conversation Memory** - Multi-turn session-based context
- **Error Handling** - Graceful handling of API failures, invalid inputs, and edge cases

---

## Architecture Overview

```
+---------------------------------------------------+
|                Browser (Web UI)                   |
|        HTML + CSS + JavaScript                    |
|        localhost:5000                              |
+-----------------------+---------------------------+
                        | HTTP REST API
+-----------------------v---------------------------+
|              Flask Backend (app.py)               |
|   Routes: / , /api/chat, /api/recipes, /api/clear|
|   Session management (per-tab memory)             |
+-----------------------+---------------------------+
                        |
+-----------------------v---------------------------+
|         CookingAgent (cooking_agent.py)            |
|         Groq LLM: llama-3.3-70b-versatile          |
|                                                    |
|   Agentic Tool-Calling Loop (max 5 iterations):   |
|   1. Send user message + tool definitions to LLM  |
|   2. LLM decides which tools to call              |
|   3. Execute tools -> return results to LLM       |
|   4. Repeat until LLM generates text response     |
|                                                    |
|   5 Tools Available:                               |
|   +-- search_recipes_local  (Local JSON KB)       |
|   +-- search_recipes_api    (TheMealDB API)       |
|   +-- get_recipe_details_local (Local KB)         |
|   +-- get_recipe_details_api   (TheMealDB)        |
|   +-- list_all_recipes         (Local KB)         |
+-----------+------------------+--------------------+
            |                  |
+-----------v------+   +-------v-----------------+
| Local JSON KB    |   | TheMealDB API           |
| 25 recipes       |   | 300+ recipes            |
| 7 cuisines       |   | Free (test key "1")     |
| 5 categories     |   | themealdb.com/api       |
+------------------+   +-------------------------+
```

### How the AI Agent Differs from a Simple Chatbot

| Feature | Simple Chatbot | This AI Agent |
|:--------|:---------------|:-------------|
| Data Source | Training data only | Real-time KB + API queries |
| Actions | Can only generate text | Can search, filter, call APIs |
| Decision Making | None | Autonomously decides which tools to use |
| Accuracy | May hallucinate recipes | Grounded in actual recipe data |
| Architecture | Single LLM call | Iterative tool-calling loop |

---

## Project Structure

```
Cooking Recipe Assistant-v1/
|-- app.py                      # Flask web server with REST API
|-- cooking_agent.py            # AI Agent (Groq LLM + 5 tools)
|-- recipe_knowledge_base.json  # Local recipe database (25 recipes)
|-- test_app.py                 # Test suite (35+ tests)
|-- requirements.txt            # Python dependencies
|-- .env                        # API keys (not in git)
|-- .gitignore                  # Git ignore rules
|-- README.md                   # This file
|-- templates/
|   +-- index.html              # Web UI template
+-- static/
    |-- style.css               # UI styling
    +-- script.js               # Frontend chat logic
```

---

## Setup Instructions

### Prerequisites
- Python 3.10 or higher
- A Groq API key (free at [console.groq.com](https://console.groq.com))
- Internet connection (for TheMealDB API)

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd "Cooking Recipe Assistant-v1"
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure API Key
Create a `.env` file in the project root:
```
GROQ_API_KEY=your_groq_api_key_here
```

### Step 4: Run the Application
```bash
python app.py
```

### Step 5: Open in Browser
Navigate to [http://localhost:5000](http://localhost:5000)

---

## Usage Examples

| User Input | Agent Behavior |
|:-----------|:---------------|
| "I have chicken, garlic, and rice" | Searches both local KB and TheMealDB API, returns ranked matches |
| "Show me the recipe for Butter Chicken" | Returns full ingredients + step-by-step instructions |
| "What vegetarian recipes do you have?" | Filters local KB by dietary tags |
| "What can I make with avocado?" | Searches API for broader results beyond local KB |
| "Show me all recipes" | Lists all 25 local recipes grouped by category |

---

## Running Tests

```bash
python test_app.py
```

Or with pytest:
```bash
pip install pytest
python -m pytest test_app.py -v
```

The test suite covers:
- Knowledge base structure validation (8 tests)
- Fuzzy matching utility (5 tests)
- Local search tool (6 tests)
- Recipe details tool (4 tests)
- List all recipes tool (3 tests)
- Tool schema definitions (3 tests)
- TheMealDB API integration (4 tests)
- Flask API endpoints (6 tests)

---

## API Endpoints

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| GET | `/` | Serve the web chat UI |
| POST | `/api/chat` | Send message, get AI response. Body: `{"message": "..."}` |
| GET | `/api/recipes` | List all local recipes by category |
| POST | `/api/clear` | Clear current chat session |

---

## Tech Stack

| Component | Technology |
|:----------|:-----------|
| Backend | Python 3.x, Flask |
| AI / LLM | Groq API (llama-3.3-70b-versatile) |
| Recipe API | TheMealDB (free, no key needed) |
| Frontend | HTML5, CSS3, JavaScript (vanilla) |
| Testing | unittest |

---

## Knowledge Base Sources

| Source | Type | Recipes | Access |
|:-------|:-----|:--------|:-------|
| Local JSON | Curated | 25 | Instant (file read) |
| TheMealDB API | Online | 300+ | HTTP request |

### Local KB Coverage
- **Cuisines**: Indian, Chinese, Italian, Mexican, American, French, Middle Eastern, Mediterranean
- **Categories**: Breakfast (5), Lunch (5), Dinner (9), Snack (2), Dessert (4)
- **Dietary Tags**: vegetarian, vegan, gluten-free

---

## License

MIT License - Built for educational purposes.
