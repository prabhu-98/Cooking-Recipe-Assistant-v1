"""Quick test for hybrid search."""
import json
from cooking_agent import search_recipes_semantic, search_recipes_hybrid, VECTOR_STORE_READY

print(f"Vector Store Ready: {VECTOR_STORE_READY}")
print()

print("=== SEMANTIC SEARCH: 'spicy Indian dinner' ===")
r = json.loads(search_recipes_semantic("spicy Indian dinner"))
if "matches" in r:
    for m in r["matches"][:3]:
        print(f"  {m['name']} ({m['cuisine']}) - {m['similarity_score']}% match")
else:
    print(f"  {r}")

print()
print("=== HYBRID SEARCH: 'quick meal' + ['chicken','garlic'] ===")
r2 = json.loads(search_recipes_hybrid("quick meal with chicken", ["chicken", "garlic"]))
print(f"  Fuzzy results: {len(r2.get('fuzzy_results', []))}")
print(f"  Semantic results: {len(r2.get('semantic_results', []))}")
print(f"  Total: {r2.get('total_results', 0)}")
if r2.get("fuzzy_results"):
    print(f"  Top fuzzy: {r2['fuzzy_results'][0]['name']}")
if r2.get("semantic_results"):
    print(f"  Top semantic: {r2['semantic_results'][0]['name']}")

print()
print("=== SEMANTIC SEARCH: 'comfort food for winter' ===")
r3 = json.loads(search_recipes_semantic("comfort food for winter"))
if "matches" in r3:
    for m in r3["matches"][:3]:
        print(f"  {m['name']} ({m['cuisine']}) - {m['similarity_score']}% match")
