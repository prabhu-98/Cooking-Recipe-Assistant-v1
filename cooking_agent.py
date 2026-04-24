"""
Cooking Recipe Assistant - AI Agent Module
==========================================
This module implements the core AI agent using Groq LLM with tool-calling capability.
It provides a dual knowledge base system (Local JSON + TheMealDB API) and exposes
5 tools that the LLM can autonomously invoke to answer user queries about recipes.

Architecture:
    User Query -> CookingAgent.chat() -> Groq LLM (with tool definitions)
        -> LLM decides which tools to call -> Execute tools -> Return results to LLM
        -> LLM generates final response (agentic loop, max 5 iterations)

Dependencies:
    - groq: Groq API SDK for LLM inference
    - requests: HTTP client for TheMealDB API calls
    - python-dotenv: Environment variable management
"""

import os
import json
import requests
from difflib import SequenceMatcher
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env file
# override=True ensures new keys are picked up even if env vars are already set
load_dotenv(override=True)


# =============================================================================
# KNOWLEDGE BASE LOADER
# =============================================================================
# Loads the local recipe knowledge base from a JSON file at startup.
# The JSON contains 25 curated recipes across 7 cuisines and 5 categories.

def load_knowledge_base():
    """
    Load recipes from the local JSON knowledge base file.
    
    Returns:
        list: A list of recipe dictionaries, each containing name, ingredients,
              instructions, dietary tags, and metadata.
    
    Raises:
        FileNotFoundError: If recipe_knowledge_base.json is not found.
        json.JSONDecodeError: If the JSON file is malformed.
    """
    kb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recipe_knowledge_base.json")
    if not os.path.exists(kb_path):
        raise FileNotFoundError(f"Knowledge base not found at: {kb_path}")
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "recipes" not in data:
        raise ValueError("Invalid knowledge base format: missing 'recipes' key")
    return data["recipes"]


# Global recipe list - loaded once at module import time for performance
RECIPES = load_knowledge_base()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def fuzzy_match(a: str, b: str) -> float:
    """
    Calculate similarity ratio between two strings using SequenceMatcher.
    
    This is used for ingredient matching so users don't need exact spelling.
    For example, "chickn" will still match "chicken" (ratio > 0.6).
    
    Args:
        a: First string to compare.
        b: Second string to compare.
    
    Returns:
        float: Similarity ratio between 0.0 (no match) and 1.0 (exact match).
    """
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


# =============================================================================
# TOOL 1: Search Local Knowledge Base by Ingredients
# =============================================================================
# Fuzzy-matches user ingredients against all 25 local recipes.
# Returns a ranked list with match percentages and missing ingredients.

def search_recipes_local(ingredients: list[str]) -> str:
    """
    Search local recipe KB for recipes matching the given ingredients.
    
    Uses three matching strategies:
    1. Fuzzy match (SequenceMatcher ratio > 0.6)
    2. Substring match (user ingredient contained in recipe ingredient)
    3. Reverse substring (recipe ingredient contained in user input)
    
    Args:
        ingredients: List of ingredient names from the user, e.g. ["chicken", "garlic"].
    
    Returns:
        str: JSON string containing ranked recipe matches with match percentages,
             matched ingredients, and missing ingredients.
    """
    if not ingredients:
        return json.dumps({"message": "No ingredients provided. Please specify at least one ingredient."})
    
    results = []
    for recipe in RECIPES:
        # Extract ingredient names from recipe for comparison
        recipe_ingredients = [ing["name"].lower() for ing in recipe["ingredients"]]
        matched = []
        
        # Check each user ingredient against each recipe ingredient
        for user_ing in ingredients:
            user_ing_lower = user_ing.lower().strip()
            if not user_ing_lower:
                continue
            for rec_ing in recipe_ingredients:
                # Match if fuzzy similarity > 0.6 OR substring match in either direction
                if (fuzzy_match(user_ing_lower, rec_ing) > 0.6 or 
                    user_ing_lower in rec_ing or 
                    rec_ing in user_ing_lower):
                    matched.append(rec_ing)
                    break
        
        # Only include recipes with at least one matched ingredient
        if matched:
            match_pct = round(len(matched) / len(recipe_ingredients) * 100)
            missing = [ing for ing in recipe_ingredients if ing not in matched]
            results.append({
                "name": recipe["name"],
                "cuisine": recipe["cuisine"],
                "category": recipe["category"],
                "difficulty": recipe["difficulty"],
                "match_percentage": match_pct,
                "matched_ingredients": matched,
                "missing_ingredients": missing[:5],
                "prep_time": recipe["prep_time"],
                "cook_time": recipe["cook_time"],
                "dietary_tags": recipe["dietary_tags"],
                "source": "local"
            })
    
    # Sort by match percentage (highest first)
    results.sort(key=lambda x: x["match_percentage"], reverse=True)
    
    if not results:
        return json.dumps({"message": "No local recipes found matching those ingredients. Try different ingredients."})
    
    return json.dumps({
        "source": "local_knowledge_base",
        "recipes_found": len(results),
        "top_matches": results[:8]
    }, indent=2)


# =============================================================================
# TOOL 2: Search TheMealDB API by Ingredient
# =============================================================================
# Calls the free TheMealDB API to find recipes from an online database of 300+ meals.
# Only accepts one ingredient at a time (API limitation on free tier).

MEALDB_BASE = "https://www.themealdb.com/api/json/v1/1"

def search_recipes_api(ingredient: str) -> str:
    """
    Search TheMealDB online API for recipes containing a specific ingredient.
    
    The free API tier only supports single-ingredient filtering.
    Returns up to 8 matching meals with names, IDs, and thumbnail URLs.
    
    Args:
        ingredient: A single ingredient name, e.g. "chicken".
    
    Returns:
        str: JSON string with matching meals from the API, or error message.
    """
    if not ingredient or not ingredient.strip():
        return json.dumps({"source": "themealdb_api", "error": "No ingredient provided."})
    
    try:
        resp = requests.get(
            f"{MEALDB_BASE}/filter.php",
            params={"i": ingredient.strip()},
            timeout=10
        )
        resp.raise_for_status()  # Raise exception for HTTP errors (4xx, 5xx)
        data = resp.json()
        
        if not data.get("meals"):
            return json.dumps({
                "source": "themealdb_api",
                "message": f"No API recipes found for '{ingredient}'."
            })
        
        # Limit to top 8 results
        meals = data["meals"][:8]
        results = [{
            "name": meal["strMeal"],
            "id": meal["idMeal"],
            "thumbnail": meal["strMealThumb"],
            "source": "themealdb_api"
        } for meal in meals]
        
        return json.dumps({
            "source": "themealdb_api",
            "recipes_found": len(results),
            "meals": results
        }, indent=2)
    
    except requests.Timeout:
        return json.dumps({"source": "themealdb_api", "error": "API request timed out. Please try again."})
    except requests.ConnectionError:
        return json.dumps({"source": "themealdb_api", "error": "Cannot reach TheMealDB API. Check internet connection."})
    except requests.RequestException as e:
        return json.dumps({"source": "themealdb_api", "error": f"API request failed: {str(e)}"})
    except Exception as e:
        return json.dumps({"source": "themealdb_api", "error": f"Unexpected error: {str(e)}"})


# =============================================================================
# TOOL 3: Get Recipe Details from Local Knowledge Base
# =============================================================================
# Looks up a specific recipe by name in the local KB using fuzzy matching.
# Returns the full recipe with ingredients (with quantities) and step-by-step instructions.

def get_recipe_details_local(recipe_name: str) -> str:
    """
    Get full recipe details from the local knowledge base by name.
    
    Uses fuzzy matching so the user doesn't need the exact recipe name.
    For example, "butter chicken" will match "Butter Chicken".
    
    Args:
        recipe_name: Name of the recipe to look up, e.g. "Butter Chicken".
    
    Returns:
        str: JSON string with full recipe details (ingredients, instructions, metadata),
             or error message if not found.
    """
    if not recipe_name or not recipe_name.strip():
        return json.dumps({"error": "No recipe name provided."})
    
    for recipe in RECIPES:
        # Match using fuzzy ratio or substring containment
        if (fuzzy_match(recipe_name, recipe["name"]) > 0.6 or 
            recipe_name.lower() in recipe["name"].lower()):
            return json.dumps({
                "source": "local_knowledge_base",
                "name": recipe["name"],
                "cuisine": recipe["cuisine"],
                "category": recipe["category"],
                "difficulty": recipe["difficulty"],
                "prep_time": recipe["prep_time"],
                "cook_time": recipe["cook_time"],
                "servings": recipe["servings"],
                "dietary_tags": recipe["dietary_tags"],
                "ingredients": [f"{ing['qty']} {ing['name']}" for ing in recipe["ingredients"]],
                "instructions": [f"Step {i+1}: {step}" for i, step in enumerate(recipe["instructions"])]
            }, indent=2)
    
    return json.dumps({"error": f"Recipe '{recipe_name}' not found in local KB. Use search_recipes_local to find available recipes."})


# =============================================================================
# TOOL 4: Get Recipe Details from TheMealDB API
# =============================================================================
# Searches the online API by meal name and returns full recipe details.
# TheMealDB stores ingredients in 20 separate fields (strIngredient1..strIngredient20).

def get_recipe_details_api(meal_name: str) -> str:
    """
    Get full recipe details from TheMealDB online API by searching meal name.
    
    The API returns ingredients in 20 separate fields which are parsed and
    combined into a clean list. Instructions are split by newline.
    
    Args:
        meal_name: Name of the meal to look up, e.g. "Chicken Tikka Masala".
    
    Returns:
        str: JSON string with full recipe details from the API, or error message.
    """
    if not meal_name or not meal_name.strip():
        return json.dumps({"source": "themealdb_api", "error": "No meal name provided."})
    
    try:
        resp = requests.get(
            f"{MEALDB_BASE}/search.php",
            params={"s": meal_name.strip()},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        if not data.get("meals"):
            return json.dumps({
                "source": "themealdb_api",
                "error": f"Recipe '{meal_name}' not found via API."
            })
        
        meal = data["meals"][0]
        
        # Parse ingredients from strIngredient1..strIngredient20 fields
        ingredients = []
        for i in range(1, 21):
            ing = meal.get(f"strIngredient{i}", "")
            measure = meal.get(f"strMeasure{i}", "")
            if ing and ing.strip():
                ingredients.append(f"{measure.strip()} {ing.strip()}")
        
        # Parse instructions - split by newlines, filter empty lines
        raw_instructions = meal.get("strInstructions", "")
        instructions = [s.strip() for s in raw_instructions.split("\r\n") if s.strip()]
        
        return json.dumps({
            "source": "themealdb_api",
            "name": meal["strMeal"],
            "category": meal.get("strCategory", ""),
            "cuisine": meal.get("strArea", ""),
            "thumbnail": meal.get("strMealThumb", ""),
            "ingredients": ingredients,
            "instructions": [f"Step {i+1}: {step}" for i, step in enumerate(instructions)]
        }, indent=2)
    
    except requests.Timeout:
        return json.dumps({"source": "themealdb_api", "error": "API request timed out."})
    except requests.ConnectionError:
        return json.dumps({"source": "themealdb_api", "error": "Cannot reach TheMealDB API."})
    except requests.RequestException as e:
        return json.dumps({"source": "themealdb_api", "error": f"API error: {str(e)}"})
    except Exception as e:
        return json.dumps({"source": "themealdb_api", "error": f"Unexpected error: {str(e)}"})


# =============================================================================
# TOOL 5: List All Local Recipes
# =============================================================================
# Returns all 25 recipes from the local KB, grouped by category.

def list_all_recipes() -> str:
    """
    List all recipes in the local knowledge base, grouped by category.
    
    Categories include: Breakfast, Lunch, Dinner, Snack, Dessert.
    Each recipe entry includes name, cuisine, difficulty, and dietary tags.
    
    Returns:
        str: JSON string with recipes organized by category.
    """
    categories = {}
    for recipe in RECIPES:
        cat = recipe["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "name": recipe["name"],
            "cuisine": recipe["cuisine"],
            "difficulty": recipe["difficulty"],
            "dietary_tags": recipe["dietary_tags"]
        })
    return json.dumps({
        "source": "local_knowledge_base",
        "total_recipes": len(RECIPES),
        "categories": categories
    }, indent=2)


# =============================================================================
# TOOL DEFINITIONS FOR GROQ LLM
# =============================================================================
# These JSON schemas tell the Groq LLM what tools are available, what arguments
# they accept, and when to use them. The LLM reads these descriptions to
# autonomously decide which tool(s) to invoke for each user query.

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_recipes_local",
            "description": "Search the LOCAL recipe knowledge base for recipes matching given ingredients. Returns ranked results with match percentages. Use this first when user mentions ingredients.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ingredients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of ingredients, e.g. ['chicken', 'garlic', 'rice']"
                    }
                },
                "required": ["ingredients"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_recipes_api",
            "description": "Search TheMealDB online API for recipes with a specific main ingredient. Use this to find MORE recipes beyond the local database. Only accepts ONE ingredient at a time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ingredient": {
                        "type": "string",
                        "description": "A single main ingredient to search for, e.g. 'chicken'"
                    }
                },
                "required": ["ingredient"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recipe_details_local",
            "description": "Get full recipe details (ingredients with quantities + step-by-step instructions) from the LOCAL knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipe_name": {
                        "type": "string",
                        "description": "Name of the recipe, e.g. 'Butter Chicken'"
                    }
                },
                "required": ["recipe_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recipe_details_api",
            "description": "Get full recipe details from TheMealDB online API. Use this for recipes found via the API search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_name": {
                        "type": "string",
                        "description": "Name of the meal to look up, e.g. 'Chicken Tikka Masala'"
                    }
                },
                "required": ["meal_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_all_recipes",
            "description": "List ALL recipes available in the local knowledge base, grouped by category. Use when user wants to browse or see all options.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# Maps tool names to their corresponding Python functions for execution
TOOL_MAP = {
    "search_recipes_local": lambda args: search_recipes_local(args["ingredients"]),
    "search_recipes_api": lambda args: search_recipes_api(args["ingredient"]),
    "get_recipe_details_local": lambda args: get_recipe_details_local(args["recipe_name"]),
    "get_recipe_details_api": lambda args: get_recipe_details_api(args["meal_name"]),
    "list_all_recipes": lambda args: list_all_recipes(),
}


# =============================================================================
# SYSTEM PROMPT
# =============================================================================
# This prompt defines the agent's personality, behavior rules, and instructions
# for how to use the available tools. It is sent with every LLM API call.

SYSTEM_PROMPT = """You are a friendly and knowledgeable Cooking Recipe Assistant. Your role is to:

1. Help users find recipes based on ingredients they have available
2. Provide detailed step-by-step cooking instructions
3. Suggest ingredient substitutions when needed
4. Give cooking tips and dietary information

You have access to TWO recipe sources:
- LOCAL Knowledge Base: 25 curated recipes with detailed instructions
- TheMealDB API: 300+ online recipes for broader coverage

RULES:
- When a user mentions ingredients, ALWAYS search the local KB first with search_recipes_local
- Then also search the API with search_recipes_api using the most prominent ingredient for wider results
- Use get_recipe_details_local for local recipes, get_recipe_details_api for API recipes
- Use list_all_recipes when users want to browse available recipes
- Be warm, encouraging, and helpful
- Format your responses clearly with emojis for better readability
- If no recipes match, suggest what additional ingredients they could get
- Mention dietary tags (vegetarian, vegan, gluten-free) when relevant
- Always indicate the source (Local KB or Online API) when presenting recipes
"""


# =============================================================================
# COOKING AGENT CLASS
# =============================================================================
# The main agent class that orchestrates the LLM and tool-calling loop.
# Each instance manages multiple conversation sessions with separate memory.

class CookingAgent:
    """
    AI Agent that uses Groq LLM with tool-calling to answer cooking queries.
    
    The agent follows an agentic loop pattern:
    1. Send user message + tool definitions to LLM
    2. If LLM returns tool calls -> execute them -> send results back
    3. Repeat until LLM returns a text response (max 5 iterations)
    
    Attributes:
        client: Groq API client instance.
        model: LLM model name (llama-3.3-70b-versatile).
        sessions: Dict mapping session IDs to conversation message histories.
    """
    
    def __init__(self):
        """
        Initialize the CookingAgent with Groq API client.
        
        Raises:
            ValueError: If GROQ_API_KEY environment variable is not set.
        """
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not set. Get a free key at https://console.groq.com "
                "and add it to the .env file."
            )
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
        self.sessions = {}  # Session-based conversation memory

    def get_messages(self, session_id: str) -> list:
        """
        Get or create the message history for a given session.
        
        Each new session starts with just the system prompt.
        Subsequent calls return the accumulated conversation history.
        
        Args:
            session_id: Unique identifier for the conversation session.
        
        Returns:
            list: List of message dictionaries for the session.
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        return self.sessions[session_id]

    def clear_session(self, session_id: str):
        """
        Clear the conversation history for a specific session.
        
        Args:
            session_id: The session to clear.
        """
        self.sessions.pop(session_id, None)

    def chat(self, user_message: str, session_id: str = "default") -> str:
        """
        Process a user message and return the agent's response.
        
        This method implements the core agentic loop:
        1. Append user message to conversation history
        2. Call Groq LLM with messages + tool definitions
        3. If LLM returns tool_calls: execute tools, append results, call LLM again
        4. Repeat step 3 until LLM returns text (or max 5 iterations reached)
        5. Return the final text response
        
        Args:
            user_message: The user's input text.
            session_id: Session identifier for conversation memory.
        
        Returns:
            str: The agent's text response with recipe information.
        """
        # Validate input
        if not user_message or not user_message.strip():
            return "Please enter a message. You can tell me what ingredients you have or ask about recipes!"
        
        messages = self.get_messages(session_id)
        messages.append({"role": "user", "content": user_message})

        # First LLM call - send user message with available tool definitions
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",   # LLM decides whether to use tools or respond directly
            max_tokens=4096
        )
        assistant_msg = response.choices[0].message
        messages.append(assistant_msg)

        # Agentic loop - iteratively process tool calls until LLM gives a text response
        max_iterations = 5  # Safety limit to prevent infinite loops
        iteration = 0
        while assistant_msg.tool_calls and iteration < max_iterations:
            iteration += 1
            
            # Execute each tool call requested by the LLM
            for tool_call in assistant_msg.tool_calls:
                fn_name = tool_call.function.name
                try:
                    fn_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}
                
                # Look up and execute the tool function
                tool_fn = TOOL_MAP.get(fn_name)
                if tool_fn:
                    result = tool_fn(fn_args)
                else:
                    result = json.dumps({"error": f"Unknown tool: {fn_name}"})
                
                # Append tool result to conversation for LLM to process
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": fn_name,
                    "content": result
                })

            # Follow-up LLM call with tool results
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=4096
            )
            assistant_msg = response.choices[0].message
            messages.append(assistant_msg)

        # Return the final text response
        return assistant_msg.content or "I'm sorry, I couldn't generate a response. Please try again."
