"""
Cooking Recipe Assistant - Test Suite
======================================
Tests for the cooking agent tools, knowledge base, and Flask API endpoints.
Run with: python -m pytest test_app.py -v
Or:       python test_app.py
"""

import json
import os
import sys
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cooking_agent import (
    load_knowledge_base,
    fuzzy_match,
    search_recipes_local,
    search_recipes_api,
    get_recipe_details_local,
    get_recipe_details_api,
    list_all_recipes,
    RECIPES,
    TOOLS,
    TOOL_MAP,
)


# =============================================================================
# TEST 1: Knowledge Base Validation
# =============================================================================

class TestKnowledgeBase(unittest.TestCase):
    """Tests for the local recipe knowledge base structure and content."""

    def test_knowledge_base_loads(self):
        """Knowledge base should load without errors."""
        recipes = load_knowledge_base()
        self.assertIsInstance(recipes, list)
        self.assertGreater(len(recipes), 0, "Knowledge base should not be empty")

    def test_recipe_count(self):
        """Knowledge base should contain exactly 25 recipes."""
        self.assertEqual(len(RECIPES), 25, f"Expected 25 recipes, got {len(RECIPES)}")

    def test_recipe_required_fields(self):
        """Each recipe should have all required fields."""
        required_fields = ["id", "name", "category", "cuisine", "difficulty",
                          "prep_time", "cook_time", "servings", "dietary_tags",
                          "ingredients", "instructions"]
        for recipe in RECIPES:
            for field in required_fields:
                self.assertIn(field, recipe, f"Recipe '{recipe.get('name', 'UNKNOWN')}' missing field: {field}")

    def test_recipe_ingredients_structure(self):
        """Each ingredient should have 'name' and 'qty' fields."""
        for recipe in RECIPES:
            for ing in recipe["ingredients"]:
                self.assertIn("name", ing, f"Ingredient in '{recipe['name']}' missing 'name'")
                self.assertIn("qty", ing, f"Ingredient in '{recipe['name']}' missing 'qty'")

    def test_recipe_has_instructions(self):
        """Each recipe should have at least one instruction step."""
        for recipe in RECIPES:
            self.assertGreater(len(recipe["instructions"]), 0,
                             f"Recipe '{recipe['name']}' has no instructions")

    def test_recipe_categories(self):
        """Recipes should cover expected categories."""
        categories = set(r["category"] for r in RECIPES)
        expected = {"Breakfast", "Lunch", "Dinner", "Snack", "Dessert"}
        self.assertEqual(categories, expected, f"Missing categories: {expected - categories}")

    def test_unique_recipe_ids(self):
        """All recipe IDs should be unique."""
        ids = [r["id"] for r in RECIPES]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate recipe IDs found")

    def test_unique_recipe_names(self):
        """All recipe names should be unique."""
        names = [r["name"] for r in RECIPES]
        self.assertEqual(len(names), len(set(names)), "Duplicate recipe names found")


# =============================================================================
# TEST 2: Utility Functions
# =============================================================================

class TestFuzzyMatch(unittest.TestCase):
    """Tests for the fuzzy string matching utility."""

    def test_exact_match(self):
        """Exact strings should return 1.0."""
        self.assertEqual(fuzzy_match("chicken", "chicken"), 1.0)

    def test_case_insensitive(self):
        """Matching should be case-insensitive."""
        self.assertEqual(fuzzy_match("Chicken", "chicken"), 1.0)

    def test_similar_strings(self):
        """Similar strings should have ratio > 0.6."""
        ratio = fuzzy_match("chickn", "chicken")
        self.assertGreater(ratio, 0.6, "Typo should still match")

    def test_different_strings(self):
        """Very different strings should have low ratio."""
        ratio = fuzzy_match("apple", "motorcycle")
        self.assertLess(ratio, 0.3, "Unrelated words should not match")

    def test_whitespace_handling(self):
        """Leading/trailing whitespace should be stripped."""
        self.assertEqual(fuzzy_match("  chicken  ", "chicken"), 1.0)


# =============================================================================
# TEST 3: Tool Functions - Local Search
# =============================================================================

class TestSearchRecipesLocal(unittest.TestCase):
    """Tests for the local recipe search tool."""

    def test_search_with_matching_ingredients(self):
        """Should find recipes matching common ingredients."""
        result = json.loads(search_recipes_local(["chicken", "garlic"]))
        self.assertIn("recipes_found", result)
        self.assertGreater(result["recipes_found"], 0, "Should find at least one recipe")

    def test_search_returns_ranked_results(self):
        """Results should be sorted by match percentage (descending)."""
        result = json.loads(search_recipes_local(["chicken", "garlic", "rice"]))
        if result.get("top_matches"):
            matches = result["top_matches"]
            for i in range(len(matches) - 1):
                self.assertGreaterEqual(
                    matches[i]["match_percentage"],
                    matches[i+1]["match_percentage"],
                    "Results should be sorted by match percentage"
                )

    def test_search_with_no_matching_ingredients(self):
        """Should return a message when no recipes match."""
        result = json.loads(search_recipes_local(["dragonfruit", "unicornmeat"]))
        self.assertIn("message", result, "Should return a 'no results' message")

    def test_search_empty_input(self):
        """Should handle empty ingredient list gracefully."""
        result = json.loads(search_recipes_local([]))
        self.assertIn("message", result)

    def test_search_result_structure(self):
        """Each match should have expected fields."""
        result = json.loads(search_recipes_local(["egg"]))
        if result.get("top_matches"):
            match = result["top_matches"][0]
            expected_fields = ["name", "cuisine", "category", "difficulty",
                             "match_percentage", "matched_ingredients", "source"]
            for field in expected_fields:
                self.assertIn(field, match, f"Missing field: {field}")

    def test_search_max_results(self):
        """Should return at most 8 results."""
        result = json.loads(search_recipes_local(["salt"]))
        if result.get("top_matches"):
            self.assertLessEqual(len(result["top_matches"]), 8)


# =============================================================================
# TEST 4: Tool Functions - Recipe Details
# =============================================================================

class TestGetRecipeDetailsLocal(unittest.TestCase):
    """Tests for the local recipe details tool."""

    def test_get_existing_recipe(self):
        """Should return full details for a known recipe."""
        result = json.loads(get_recipe_details_local("Butter Chicken"))
        self.assertEqual(result["name"], "Butter Chicken")
        self.assertIn("ingredients", result)
        self.assertIn("instructions", result)
        self.assertGreater(len(result["ingredients"]), 0)
        self.assertGreater(len(result["instructions"]), 0)

    def test_get_recipe_fuzzy_name(self):
        """Should match recipe names with fuzzy matching."""
        result = json.loads(get_recipe_details_local("butter chicken"))
        self.assertNotIn("error", result, "Should match case-insensitively")

    def test_get_nonexistent_recipe(self):
        """Should return error for unknown recipe."""
        result = json.loads(get_recipe_details_local("Alien Space Soup"))
        self.assertIn("error", result)

    def test_get_recipe_empty_name(self):
        """Should handle empty recipe name."""
        result = json.loads(get_recipe_details_local(""))
        self.assertIn("error", result)


# =============================================================================
# TEST 5: Tool Functions - List All Recipes
# =============================================================================

class TestListAllRecipes(unittest.TestCase):
    """Tests for the list all recipes tool."""

    def test_list_returns_categories(self):
        """Should return recipes grouped by category."""
        result = json.loads(list_all_recipes())
        self.assertIn("categories", result)
        self.assertIn("source", result)

    def test_list_all_categories_present(self):
        """All expected categories should be present."""
        result = json.loads(list_all_recipes())
        categories = result["categories"]
        for cat in ["Breakfast", "Lunch", "Dinner", "Snack", "Dessert"]:
            self.assertIn(cat, categories, f"Missing category: {cat}")

    def test_list_total_count(self):
        """Total recipe count should be 25."""
        result = json.loads(list_all_recipes())
        total = sum(len(recipes) for recipes in result["categories"].values())
        self.assertEqual(total, 25, f"Expected 25 total recipes, got {total}")


# =============================================================================
# TEST 6: Tool Definitions
# =============================================================================

class TestToolDefinitions(unittest.TestCase):
    """Tests for the Groq tool schema definitions."""

    def test_tool_count(self):
        """Should have exactly 5 tool definitions."""
        self.assertEqual(len(TOOLS), 5)

    def test_tool_map_matches_definitions(self):
        """TOOL_MAP should have entries for all defined tools."""
        tool_names = [t["function"]["name"] for t in TOOLS]
        for name in tool_names:
            self.assertIn(name, TOOL_MAP, f"Tool '{name}' missing from TOOL_MAP")

    def test_tool_schema_structure(self):
        """Each tool should have required schema fields."""
        for tool in TOOLS:
            self.assertEqual(tool["type"], "function")
            self.assertIn("name", tool["function"])
            self.assertIn("description", tool["function"])
            self.assertIn("parameters", tool["function"])


# =============================================================================
# TEST 7: TheMealDB API Integration
# =============================================================================

class TestMealDBApi(unittest.TestCase):
    """Tests for TheMealDB API integration (requires internet)."""

    def test_api_search_valid_ingredient(self):
        """Should return results for a common ingredient."""
        result = json.loads(search_recipes_api("chicken"))
        # API may be unavailable, so check for either results or graceful error
        if "error" not in result:
            self.assertIn("meals", result)
            self.assertGreater(result["recipes_found"], 0)
        else:
            # API unavailable - this is acceptable in offline environments
            self.assertIn("error", result)

    def test_api_search_empty_ingredient(self):
        """Should handle empty ingredient gracefully."""
        result = json.loads(search_recipes_api(""))
        self.assertIn("error", result)

    def test_api_details_valid_meal(self):
        """Should return recipe details for a known meal."""
        result = json.loads(get_recipe_details_api("Arrabiata"))
        if "error" not in result:
            self.assertIn("name", result)
            self.assertIn("ingredients", result)
            self.assertIn("instructions", result)

    def test_api_details_unknown_meal(self):
        """Should return error for unknown meal name."""
        result = json.loads(get_recipe_details_api("xyznonexistentmeal123"))
        self.assertIn("error", result)


# =============================================================================
# TEST 8: Flask API Endpoints
# =============================================================================

class TestFlaskAPI(unittest.TestCase):
    """Tests for Flask REST API endpoints."""

    @classmethod
    def setUpClass(cls):
        """Set up Flask test client."""
        from app import app
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        cls.client = app.test_client()

    def test_index_page_loads(self):
        """GET / should return the HTML page."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Chef AI", response.data)

    def test_recipes_endpoint(self):
        """GET /api/recipes should return recipe categories."""
        response = self.client.get("/api/recipes")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("categories", data)

    def test_chat_empty_message(self):
        """POST /api/chat with empty message should return 400."""
        response = self.client.post("/api/chat",
            json={"message": ""},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_chat_no_json(self):
        """POST /api/chat without JSON body should return 400."""
        response = self.client.post("/api/chat",
            data="not json",
            content_type="text/plain"
        )
        self.assertEqual(response.status_code, 400)

    def test_clear_session(self):
        """POST /api/clear should return success status."""
        response = self.client.post("/api/clear")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "cleared")

    def test_404_handler(self):
        """Unknown endpoints should return 404."""
        response = self.client.get("/api/nonexistent")
        self.assertEqual(response.status_code, 404)


# =============================================================================
# MAIN - Run Tests
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  Cooking Recipe Assistant - Test Suite")
    print("=" * 55 + "\n")
    unittest.main(verbosity=2)
