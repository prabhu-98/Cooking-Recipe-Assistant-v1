"""
Cooking Recipe Assistant — LangChain Version
=============================================
This module implements the SAME Cooking Recipe Assistant using the LangChain
framework. It demonstrates how LangChain abstracts the agentic tool-calling
loop, compared to the custom implementation in the main project.

Key Differences from the Custom Version:
    - Uses @tool decorator instead of manual TOOLS JSON schemas
    - Uses ChatGroq wrapper instead of raw Groq SDK
    - Uses create_tool_calling_agent() instead of a manual while-loop
    - Uses AgentExecutor to manage the loop automatically

Architecture:
    User Query -> LangChain AgentExecutor -> ChatGroq LLM
        -> LLM picks tools -> AgentExecutor runs them -> feeds results back
        -> Repeats until LLM returns text (managed by AgentExecutor)
"""

import os
import sys
import json
import requests
from difflib import SequenceMatcher
from dotenv import load_dotenv

# LangChain imports
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor

# Load environment variables
load_dotenv(override=True)

# ─────────────────────────────────────────────────────────────────
# KNOWLEDGE BASE LOADER (shared with main project)
# ─────────────────────────────────────────────────────────────────

def load_knowledge_base():
    """Load recipes from the parent directory's JSON knowledge base."""
    kb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "recipe_knowledge_base.json")
    if not os.path.exists(kb_path):
        raise FileNotFoundError(f"Knowledge base not found at: {kb_path}")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["recipes"]

RECIPES = load_knowledge_base()


def fuzzy_match(a: str, b: str) -> float:
    """Calculate string similarity ratio for ingredient matching."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


# ─────────────────────────────────────────────────────────────────
# LANGCHAIN TOOLS (using @tool decorator)
# ─────────────────────────────────────────────────────────────────
# In LangChain, tools are defined as Python functions with the @tool
# decorator. LangChain auto-generates the JSON schema from the
# function signature and docstring — no manual schema needed.

MEALDB_BASE = "https://www.themealdb.com/api/json/v1/1"


@tool
def search_recipes_local(ingredients: list[str]) -> str:
    """Search the LOCAL recipe knowledge base for recipes matching given ingredients.
    Uses fuzzy string matching. Returns ranked results with match percentages.
    Use this when user mentions specific ingredients they have."""
    if not ingredients:
        return json.dumps({"message": "No ingredients provided."})
    
    results = []
    for recipe in RECIPES:
        recipe_ingredients = [ing["name"].lower() for ing in recipe["ingredients"]]
        matched = []
        for user_ing in ingredients:
            user_ing_lower = user_ing.lower().strip()
            if not user_ing_lower:
                continue
            for rec_ing in recipe_ingredients:
                if (fuzzy_match(user_ing_lower, rec_ing) > 0.6 or
                    user_ing_lower in rec_ing or rec_ing in user_ing_lower):
                    matched.append(rec_ing)
                    break
        if matched:
            match_pct = round(len(matched) / len(recipe_ingredients) * 100)
            missing = [ing for ing in recipe_ingredients if ing not in matched]
            results.append({
                "name": recipe["name"], "cuisine": recipe["cuisine"],
                "match_percentage": match_pct,
                "matched_ingredients": matched,
                "missing_ingredients": missing[:5],
                "dietary_tags": recipe["dietary_tags"], "source": "local"
            })
    results.sort(key=lambda x: x["match_percentage"], reverse=True)
    if not results:
        return json.dumps({"message": "No local recipes found matching those ingredients."})
    return json.dumps({"source": "local_kb", "recipes_found": len(results), "top_matches": results[:8]}, indent=2)


@tool
def search_recipes_api(ingredient: str) -> str:
    """Search TheMealDB online API for recipes with a specific ingredient.
    Only accepts ONE ingredient at a time. Use for broader recipe coverage."""
    if not ingredient or not ingredient.strip():
        return json.dumps({"error": "No ingredient provided."})
    try:
        resp = requests.get(f"{MEALDB_BASE}/filter.php", params={"i": ingredient.strip()}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("meals"):
            return json.dumps({"message": f"No API recipes found for '{ingredient}'."})
        meals = data["meals"][:8]
        results = [{"name": m["strMeal"], "id": m["idMeal"], "thumbnail": m["strMealThumb"]} for m in meals]
        return json.dumps({"source": "themealdb_api", "recipes_found": len(results), "meals": results}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"API error: {str(e)}"})


@tool
def get_recipe_details_local(recipe_name: str) -> str:
    """Get full recipe details (ingredients with quantities + step-by-step instructions)
    from the LOCAL knowledge base. Use this to show a complete recipe."""
    if not recipe_name:
        return json.dumps({"error": "No recipe name provided."})
    for recipe in RECIPES:
        if (fuzzy_match(recipe_name, recipe["name"]) > 0.6 or
            recipe_name.lower() in recipe["name"].lower()):
            return json.dumps({
                "name": recipe["name"], "cuisine": recipe["cuisine"],
                "difficulty": recipe["difficulty"],
                "prep_time": recipe["prep_time"], "cook_time": recipe["cook_time"],
                "servings": recipe["servings"], "dietary_tags": recipe["dietary_tags"],
                "ingredients": [f"{ing['qty']} {ing['name']}" for ing in recipe["ingredients"]],
                "instructions": [f"Step {i+1}: {s}" for i, s in enumerate(recipe["instructions"])]
            }, indent=2)
    return json.dumps({"error": f"Recipe '{recipe_name}' not found in local KB."})


@tool
def get_recipe_details_api(meal_name: str) -> str:
    """Get full recipe details from TheMealDB online API by meal name.
    Use this for recipes found via the API search."""
    if not meal_name:
        return json.dumps({"error": "No meal name provided."})
    try:
        resp = requests.get(f"{MEALDB_BASE}/search.php", params={"s": meal_name.strip()}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("meals"):
            return json.dumps({"error": f"'{meal_name}' not found via API."})
        meal = data["meals"][0]
        ingredients = []
        for i in range(1, 21):
            ing = meal.get(f"strIngredient{i}", "")
            measure = meal.get(f"strMeasure{i}", "")
            if ing and ing.strip():
                ingredients.append(f"{measure.strip()} {ing.strip()}")
        instructions = [s.strip() for s in meal.get("strInstructions", "").split("\r\n") if s.strip()]
        return json.dumps({
            "name": meal["strMeal"], "cuisine": meal.get("strArea", ""),
            "ingredients": ingredients,
            "instructions": [f"Step {i+1}: {s}" for i, s in enumerate(instructions)]
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"API error: {str(e)}"})


@tool
def list_all_recipes() -> str:
    """List ALL recipes available in the local knowledge base, grouped by category.
    Use when user wants to browse or see all available options."""
    categories = {}
    for recipe in RECIPES:
        cat = recipe["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "name": recipe["name"], "cuisine": recipe["cuisine"],
            "difficulty": recipe["difficulty"], "dietary_tags": recipe["dietary_tags"]
        })
    return json.dumps({"total_recipes": len(RECIPES), "categories": categories}, indent=2)


# ─────────────────────────────────────────────────────────────────
# LANGCHAIN AGENT SETUP
# ─────────────────────────────────────────────────────────────────

# Collect all tools
tools = [search_recipes_local, search_recipes_api, get_recipe_details_local,
         get_recipe_details_api, list_all_recipes]

# System prompt (same personality as custom version)
SYSTEM_PROMPT = """You are a friendly and knowledgeable Cooking Recipe Assistant. Your role is to:
1. Help users find recipes based on ingredients they have available
2. Provide detailed step-by-step cooking instructions
3. Suggest ingredient substitutions when needed
4. Give cooking tips and dietary information

You have access to a LOCAL Knowledge Base (25 curated recipes) and TheMealDB API (300+ online recipes).

RULES:
- When a user mentions ingredients, search the local KB first with search_recipes_local
- Then search the API with search_recipes_api for wider results
- Use get_recipe_details_local for local recipes, get_recipe_details_api for API recipes
- Use list_all_recipes when users want to browse
- Be warm, encouraging, and helpful
- Format responses clearly with emojis
- Mention dietary tags when relevant
"""

# LangChain prompt template with memory support
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])


class LangChainCookingAgent:
    """
    LangChain-based Cooking Recipe Assistant.
    
    Compare this with CookingAgent in cooking_agent.py:
    - Custom: Manual while-loop, raw Groq SDK, hand-written JSON schemas
    - LangChain: AgentExecutor handles the loop, @tool decorator generates schemas
    """
    
    def __init__(self):
        """Initialize the LangChain agent with Groq LLM."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set.")
        
        # LangChain's Groq wrapper (vs raw Groq SDK in custom version)
        self.llm = ChatGroq(
            api_key=api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0,
            max_tokens=4096
        )
        
        # Create tool-calling agent (LangChain builds the loop for us)
        agent = create_tool_calling_agent(self.llm, tools, prompt)
        
        # AgentExecutor manages: tool execution, result feeding, iteration limit
        self.executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,        # Print the reasoning steps (great for demo)
            max_iterations=5,    # Same safety limit as custom version
            handle_parsing_errors=True
        )
        
        # Session memory
        self.sessions = {}
    
    def chat(self, user_message: str, session_id: str = "default") -> str:
        """
        Process a user message using LangChain's AgentExecutor.
        
        Notice how much simpler this is vs the custom version:
        - No manual while-loop
        - No manual tool_call parsing
        - No manual message appending
        AgentExecutor handles ALL of that internally.
        """
        if not user_message or not user_message.strip():
            return "Please enter a message!"
        
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        try:
            result = self.executor.invoke({
                "input": user_message,
                "chat_history": self.sessions[session_id]
            })
            
            # Store conversation in memory
            from langchain_core.messages import HumanMessage, AIMessage
            self.sessions[session_id].append(HumanMessage(content=user_message))
            self.sessions[session_id].append(AIMessage(content=result["output"]))
            
            return result["output"]
        except Exception as e:
            return f"Error: {str(e)}"
    
    def clear_session(self, session_id: str):
        """Clear conversation history for a session."""
        self.sessions.pop(session_id, None)


# ─────────────────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    
    print("=" * 55)
    print("  LangChain Cooking Recipe Assistant")
    print("=" * 55)
    
    agent = LangChainCookingAgent()
    
    print("\nTest 1: Ingredient search")
    print("-" * 40)
    response = agent.chat("I have chicken and garlic")
    print(f"\nAgent: {response[:500]}")
    
    print("\n\nTest 2: List all recipes")
    print("-" * 40)
    response = agent.chat("Show me all recipes")
    print(f"\nAgent: {response[:500]}")
    
    print("\n\nDone! LangChain agent is working.")
