from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from openai import OpenAI
from app.core.config import settings

router = APIRouter()

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Model pricing information (per 1M tokens)
# Source: https://openai.com/api/pricing/
MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00, "description": "Advanced model - Better accuracy for complex documents"},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "description": "Fast and affordable - Best for most use cases"},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00, "description": "Most capable - Highest quality extraction"},
    "gpt-4": {"input": 30.00, "output": 60.00, "description": "Legacy GPT-4 - High quality"},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50, "description": "Fast and economical - Basic extraction"},
}


@router.get("/available")
def get_available_models() -> List[Dict[str, Any]]:
    """
    Get list of available GPT models with pricing information.
    Fetches real-time model list from OpenAI API and combines with pricing data.
    """
    try:
        # Fetch available models from OpenAI
        models_response = client.models.list()
        
        # Filter for GPT models suitable for chat completion
        available_models = []
        gpt_models = [m for m in models_response.data if m.id.startswith('gpt-')]
        
        # Filter to only include models we have pricing for
        for model in gpt_models:
            model_id = model.id
            if model_id in MODEL_PRICING:
                pricing = MODEL_PRICING[model_id]
                available_models.append({
                    "id": model_id,
                    "name": model_id.upper().replace("-", " ").replace("GPT ", "GPT-"),
                    "inputPrice": pricing["input"],
                    "outputPrice": pricing["output"],
                    "description": pricing["description"],
                    "created": model.created
                })
        
        # Sort by input price (cheapest first)
        available_models.sort(key=lambda x: x["inputPrice"])
        
        # If no models found, return fallback list
        if not available_models:
            return [
                {
                    "id": "gpt-4o-mini",
                    "name": "GPT-4o Mini",
                    "inputPrice": 0.15,
                    "outputPrice": 0.60,
                    "description": "Fast and affordable - Best for most use cases",
                    "created": None
                },
                {
                    "id": "gpt-4o",
                    "name": "GPT-4o",
                    "inputPrice": 2.50,
                    "outputPrice": 10.00,
                    "description": "Advanced model - Better accuracy for complex documents",
                    "created": None
                },
                {
                    "id": "gpt-4-turbo",
                    "name": "GPT-4 Turbo",
                    "inputPrice": 10.00,
                    "outputPrice": 30.00,
                    "description": "Most capable - Highest quality extraction",
                    "created": None
                }
            ]
        
        return available_models
        
    except Exception as e:
        # If API call fails, return fallback models
        print(f"Failed to fetch models from OpenAI: {str(e)}")
        return [
            {
                "id": "gpt-4o-mini",
                "name": "GPT-4o Mini",
                "inputPrice": 0.15,
                "outputPrice": 0.60,
                "description": "Fast and affordable - Best for most use cases",
                "created": None
            },
            {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "inputPrice": 2.50,
                "outputPrice": 10.00,
                "description": "Advanced model - Better accuracy for complex documents",
                "created": None
            },
            {
                "id": "gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "inputPrice": 10.00,
                "outputPrice": 30.00,
                "description": "Most capable - Highest quality extraction",
                "created": None
            }
        ]


@router.get("/pricing")
def get_model_pricing() -> Dict[str, Dict[str, Any]]:
    """
    Get detailed pricing information for all supported models.
    """
    return MODEL_PRICING
