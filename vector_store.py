"""
Cooking Recipe Assistant - Vector Store Module (ChromaDB)
==========================================================
This module implements a semantic search layer using ChromaDB as the vector
database and Sentence Transformers for generating embeddings.

Each recipe is stored as a rich text document combining its name, cuisine,
category, ingredients, dietary tags, and description. This allows the vector
search to understand queries like "warm comforting winter soup" or "quick
healthy breakfast" — things that fuzzy matching cannot handle.

Architecture:
    Recipe JSON → Build rich text document per recipe → Embed with all-MiniLM-L6-v2
    → Store in ChromaDB → Query with natural language → Return semantically similar recipes

Dependencies:
    - chromadb: Vector database for storing and querying embeddings
    - sentence-transformers: Pre-trained models for generating text embeddings
"""

import os
import json
import logging
import chromadb
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Embedding model - lightweight (80MB), fast, good quality for short texts
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ChromaDB collection name
COLLECTION_NAME = "recipes"

# Path for persistent ChromaDB storage
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")


# =============================================================================
# RECIPE DOCUMENT BUILDER
# =============================================================================

def build_recipe_document(recipe: dict) -> str:
    """
    Convert a recipe dictionary into a rich text document for embedding.
    
    This document is what gets vectorized. The richer and more descriptive
    it is, the better the semantic search quality will be. We include:
    - Recipe name and cuisine for identity
    - Category and difficulty for filtering context
    - All ingredient names for ingredient-based semantic search
    - Dietary tags for lifestyle queries ("vegan", "gluten-free")
    - Cooking times for time-based queries ("quick", "under 30 min")
    
    Args:
        recipe: A recipe dictionary from the knowledge base.
    
    Returns:
        str: A rich text document combining all searchable recipe attributes.
    
    Example output:
        "Butter Chicken. Indian Dinner recipe. Difficulty: Medium.
         Ingredients: chicken thigh, yogurt, butter, onion, garlic, ginger, ...
         Dietary tags: gluten-free. Prep time: 20 min. Cook time: 30 min.
         A rich and creamy Indian curry made with tender chicken pieces."
    """
    ingredients = ", ".join([ing["name"] for ing in recipe["ingredients"]])
    tags = ", ".join(recipe["dietary_tags"]) if recipe["dietary_tags"] else "none"
    
    document = (
        f"{recipe['name']}. "
        f"{recipe['cuisine']} {recipe['category']} recipe. "
        f"Difficulty: {recipe['difficulty']}. "
        f"Ingredients: {ingredients}. "
        f"Dietary tags: {tags}. "
        f"Prep time: {recipe['prep_time']}. Cook time: {recipe['cook_time']}. "
        f"Servings: {recipe['servings']}."
    )
    return document


# =============================================================================
# RECIPE VECTOR STORE CLASS
# =============================================================================

class RecipeVectorStore:
    """
    Manages the ChromaDB vector database for semantic recipe search.
    
    This class handles:
    1. Loading/creating the ChromaDB persistent database
    2. Embedding all 25 recipes on first run (cached thereafter)
    3. Querying the database with natural language for semantic matches
    
    The embedding model (all-MiniLM-L6-v2) is downloaded on first use
    and cached locally by sentence-transformers.
    
    Attributes:
        model: SentenceTransformer model instance for encoding text.
        client: ChromaDB persistent client.
        collection: ChromaDB collection storing recipe embeddings.
    """
    
    def __init__(self, recipes: list):
        """
        Initialize the vector store with recipe data.
        
        On first run:
        - Downloads the embedding model (~80MB)
        - Creates a ChromaDB persistent database
        - Embeds all recipes and stores them
        
        On subsequent runs:
        - Loads the cached model and existing database
        - Only re-indexes if recipe count has changed
        
        Args:
            recipes: List of recipe dictionaries from the knowledge base.
        """
        logger.info("Initializing Vector Store with ChromaDB...")
        
        # Load the embedding model (cached after first download)
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        
        # Initialize ChromaDB with persistent storage
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        
        # Get or create the recipes collection
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Recipe embeddings for semantic search"}
        )
        
        # Index recipes if the collection is empty or count mismatch
        existing_count = self.collection.count()
        if existing_count != len(recipes):
            logger.info(f"Indexing {len(recipes)} recipes into ChromaDB (was {existing_count})...")
            self._index_recipes(recipes)
        else:
            logger.info(f"Vector store already has {existing_count} recipes indexed.")
    
    def _index_recipes(self, recipes: list):
        """
        Embed and store all recipes in ChromaDB.
        
        Each recipe is stored with:
        - ID: Recipe's unique integer ID as string
        - Document: Rich text representation (for re-embedding)
        - Embedding: 384-dimensional vector from all-MiniLM-L6-v2
        - Metadata: Structured fields for post-filtering
        
        Args:
            recipes: List of recipe dictionaries to index.
        """
        # Clear existing data to avoid duplicates
        # Delete the collection and recreate it
        self.client.delete_collection(COLLECTION_NAME)
        self.collection = self.client.create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Recipe embeddings for semantic search"}
        )
        
        # Build documents and metadata for all recipes
        documents = []
        metadatas = []
        ids = []
        
        for recipe in recipes:
            doc = build_recipe_document(recipe)
            documents.append(doc)
            
            # Store structured metadata for filtering and display
            metadatas.append({
                "name": recipe["name"],
                "cuisine": recipe["cuisine"],
                "category": recipe["category"],
                "difficulty": recipe["difficulty"],
                "dietary_tags": ", ".join(recipe["dietary_tags"]) if recipe["dietary_tags"] else "none",
                "prep_time": recipe["prep_time"],
                "cook_time": recipe["cook_time"],
                "servings": recipe["servings"]
            })
            ids.append(str(recipe["id"]))
        
        # Generate embeddings for all documents at once (batch processing)
        logger.info("Generating embeddings for all recipes...")
        embeddings = self.model.encode(documents).tolist()
        
        # Store in ChromaDB
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        logger.info(f"Successfully indexed {len(recipes)} recipes in ChromaDB.")
    
    def search(self, query: str, n_results: int = 5) -> list:
        """
        Perform semantic search on the recipe collection.
        
        Embeds the query text using the same model, then finds the closest
        recipe embeddings using cosine similarity (ChromaDB default).
        
        Args:
            query: Natural language search query (e.g., "spicy Indian dinner").
            n_results: Maximum number of results to return.
        
        Returns:
            list: List of dicts, each containing recipe metadata and similarity score.
                  Sorted by relevance (most similar first).
        """
        if not query or not query.strip():
            return []
        
        # Embed the query
        query_embedding = self.model.encode([query.strip()]).tolist()
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(n_results, self.collection.count()),
            include=["metadatas", "documents", "distances"]
        )
        
        # Format results
        formatted = []
        if results and results["metadatas"] and results["metadatas"][0]:
            for i, metadata in enumerate(results["metadatas"][0]):
                # ChromaDB returns L2 distance; convert to similarity score
                # Lower distance = more similar
                distance = results["distances"][0][i] if results["distances"] else 0
                similarity = round(max(0, 1 - distance / 2) * 100, 1)  # Normalize to 0-100%
                
                formatted.append({
                    "name": metadata.get("name", ""),
                    "cuisine": metadata.get("cuisine", ""),
                    "category": metadata.get("category", ""),
                    "difficulty": metadata.get("difficulty", ""),
                    "dietary_tags": metadata.get("dietary_tags", ""),
                    "prep_time": metadata.get("prep_time", ""),
                    "cook_time": metadata.get("cook_time", ""),
                    "similarity_score": similarity,
                    "source": "semantic_search"
                })
        
        return formatted
