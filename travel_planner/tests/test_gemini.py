import os
from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai
from pathlib import Path
import sys

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini client with API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

class Recipe(BaseModel):
    recipe_name: str
    ingredients: list[str]

def test_gemini_recipe_suggestion():
    """Test function to get recipe suggestions from Gemini."""
    try:
        # Initialize the client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        print("Sending request to Gemini...")
        
        # Make the API request
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="List a few popular cookie recipes, and include the amounts of ingredients.",
            config={
                "response_mime_type": "application/json",
                "response_schema": list[Recipe],
            },
        )
        
        print("\nResponse as JSON string:")
        print(response.text)
        
        print("\nParsed response as objects:")
        my_recipes: list[Recipe] = response.parsed
        for i, recipe in enumerate(my_recipes, 1):
            print(f"\nRecipe {i}: {recipe.recipe_name}")
            print("Ingredients:")
            for ingredient in recipe.ingredients:
                print(f"- {ingredient}")
                
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    test_gemini_recipe_suggestion()
