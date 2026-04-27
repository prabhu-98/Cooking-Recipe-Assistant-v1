# Cooking Recipe Assistant - AI Agent

An AI-powered cooking recipe assistant that suggests recipes based on available ingredients and provides step-by-step cooking instructions. Built as an **AI Agent** (not a simple chatbot) using Groq LLM with autonomous tool-calling and a **Hybrid Search Architecture** combining Fuzzy Matching + Semantic Vector Search (ChromaDB) + TheMealDB API.

---

## Features

- **AI Agent with Tool-Calling** — Uses Groq LLM (llama-3.3-70b) with 7 autonomous tools
- **Hybrid Search (RAG)** — Combines fuzzy ingredient matching + ChromaDB semantic vector search for zero-hallucination results
- **Triple Knowledge Base** — Local JSON (25 recipes) + ChromaDB Vector DB + TheMealDB API (300+ online recipes)
- **Semantic Search** — Understands queries like "comfort food for winter" or "quick healthy breakfast" using AI embeddings
- **Fuzzy Ingredient Matching** — Handles typos and partial names (e.g., "chickn" matches "chicken")
- **Step-by-Step Instructions** — Detailed cooking steps with ingredient quantities
- **Dietary Filters** — Vegetarian, vegan, and gluten-free tags
- **Web UI** — Premium Cortex-inspired chat interface with glassmorphism design
- **Conversation Memory** — Multi-turn session-based context
- **48 Automated Tests** — Comprehensive test suite covering all components

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
|   7 Tools Available:                               |
|   +-- search_recipes_hybrid   (Fuzzy + Semantic) |
|   +-- search_recipes_semantic (ChromaDB vectors) |
|   +-- search_recipes_local    (Fuzzy match)      |
|   +-- search_recipes_api      (TheMealDB API)   |
|   +-- get_recipe_details_local (Local KB)        |
|   +-- get_recipe_details_api   (TheMealDB)       |
|   +-- list_all_recipes         (Local KB)        |
+-----------+----------+-----------+----------------+
            |          |           |
+-----------v--+ +-----v-------+ +v-----------------+
| Local JSON   | | ChromaDB    | | TheMealDB API    |
| 25 recipes   | | Vector DB   | | 300+ recipes     |
| Fuzzy match  | | Semantic    | | Online (free)    |
+--------------+ +-------------+ +------------------+
```

### Hybrid Search: Why Three Methods?

| Search Method | Best For | How It Works | Weakness |
|:-------------|:---------|:-------------|:---------|
| **Fuzzy Match** | Exact ingredients ("chicken", "garlic") | Compares character strings with SequenceMatcher | Can't understand "comfort food" or "quick lunch" |
| **Semantic Search** | Abstract queries ("spicy Indian dinner") | AI embeddings via all-MiniLM-L6-v2 + ChromaDB | May match by vibe, not exact ingredients |
| **Hybrid** | Everything | Runs BOTH fuzzy + semantic, deduplicates | Slightly slower (runs two searches) |

> The hybrid approach prevents hallucination (fuzzy ensures real ingredients) while enabling discovery (semantic finds contextually relevant recipes).

### How the AI Agent Differs from a Simple Chatbot

| Feature | Simple Chatbot | This AI Agent |
|:--------|:---------------|:-------------|
| Data Source | Training data only (may hallucinate) | Real-time KB + Vector DB + API queries |
| Actions | Can only generate text | Can search, filter, call APIs autonomously |
| Search | None | Hybrid: Fuzzy + Semantic + API |
| Decision Making | None | Autonomously decides which tools to use |
| Accuracy | May invent recipes | Grounded in actual recipe data (RAG) |
| Architecture | Single LLM call | Iterative tool-calling loop (max 5 rounds) |

---

## Project Structure

```
Cooking Recipe Assistant-v1/
|-- app.py                      # Flask web server with REST API
|-- cooking_agent.py            # AI Agent (Groq LLM + 7 tools + hybrid search)
|-- vector_store.py             # ChromaDB vector database + sentence embeddings
|-- recipe_knowledge_base.json  # Local recipe database (25 recipes)
|-- test_app.py                 # Test suite (48 tests)
|-- requirements.txt            # Python dependencies
|-- Project_Documentation.md    # Detailed 10-section technical documentation
|-- .env                        # API keys (not in git)
|-- .gitignore                  # Git ignore rules
|-- README.md                   # This file
|-- templates/
|   +-- index.html              # Web UI template (Cortex-inspired design)
+-- static/
    |-- style.css               # Glassmorphism UI styling
    +-- script.js               # Frontend chat logic + markdown rendering
```

---

## Setup Instructions

### Prerequisites
- Python 3.10 or higher
- A Groq API key (free at [console.groq.com](https://console.groq.com))
- Internet connection (for TheMealDB API + first-time embedding model download)

### Step 1: Clone the Repository
```bash
git clone https://github.com/prabhu-98/Cooking-Recipe-Assistant-v1.git
cd Cooking-Recipe-Assistant-v1
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```
> Note: First run will download the `all-MiniLM-L6-v2` embedding model (~80MB) and index recipes into ChromaDB. This is cached for subsequent runs.

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

| User Input | Search Method Used | Agent Behavior |
|:-----------|:-------------------|:---------------|
| "I have chicken, garlic, and rice" | **Hybrid** (Fuzzy + Semantic) | Finds exact ingredient matches AND semantically related recipes |
| "Something spicy and Indian" | **Semantic** (ChromaDB) | Finds Butter Chicken, Dal Tadka by meaning — not possible with fuzzy |
| "Quick healthy breakfast" | **Semantic** (ChromaDB) | Finds Banana Smoothie, Mango Lassi by concept |
| "Show me the recipe for Butter Chicken" | **Fuzzy** (Local KB) | Returns full ingredients + step-by-step instructions |
| "What can I make with avocado?" | **Hybrid + API** | Searches local KB + TheMealDB for broader results |
| "Show me all recipes" | **List** (Local KB) | Lists all 25 local recipes grouped by category |

---

## Running Tests

```bash
python test_app.py
```

Or with pytest:
```bash
python -m pytest test_app.py -v
```

### Test Coverage (48 Tests)

| Category | Tests | What It Validates |
|:---------|:------|:-----------------|
| Knowledge Base | 8 | JSON integrity, schema, unique IDs/names, categories |
| Fuzzy Matching | 5 | Exact match, case-insensitive, typos, whitespace |
| Local Search | 6 | Ingredient matching, ranking, empty inputs, result limits |
| Recipe Details | 4 | Full recipe retrieval, fuzzy name match, error cases |
| List Recipes | 3 | Category grouping, completeness, count validation |
| **Semantic Search** | **5** | **ChromaDB init, descriptive queries, dietary queries, similarity scores** |
| **Hybrid Search** | **4** | **Combined results, deduplication, query-only mode, method labels** |
| Tool Definitions | 3 | 7 tools registered, schema structure, TOOL_MAP completeness |
| TheMealDB API | 4 | Online search, empty inputs, unknown meals, error handling |
| Flask API | 6 | Routes, status codes, JSON validation, session clearing |

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
| Vector Database | ChromaDB (persistent, local) |
| Embeddings | Sentence Transformers (all-MiniLM-L6-v2) |
| Recipe API | TheMealDB (free, no key needed) |
| Frontend | HTML5, CSS3, JavaScript (vanilla) |
| Testing | unittest (48 tests) |

---

## Knowledge Base Sources

| Source | Type | Recipes | Search Method | Access |
|:-------|:-----|:--------|:-------------|:-------|
| Local JSON | Curated | 25 | Fuzzy matching | Instant (file read) |
| ChromaDB | Vector DB | 25 (indexed) | Semantic similarity | Instant (local embeddings) |
| TheMealDB API | Online | 300+ | Keyword filter | HTTP request |

### Local KB Coverage
- **Cuisines**: Indian, Chinese, Italian, Mexican, American, French, Middle Eastern, Mediterranean
- **Categories**: Breakfast (5), Lunch (5), Dinner (9), Snack (2), Dessert (4)
- **Dietary Tags**: vegetarian, vegan, gluten-free

---

## License

MIT License - Built for educational purposes.
