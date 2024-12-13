###############################################################################
# routes_llm.py
#
# Purpose:
# Provides FastAPI routes for LLM-related operations. Now we have two endpoints:
# 1. POST /llm/chat_complete: For text-based chat completions using the chat model (llama3.1 (8b)).
# 2. POST /llm/vision: For vision-based reasoning with images using the vision model (llama3.2-vision (11b)).
#
# Key Changes:
# - Added a VisionLLMRequest model and a new endpoint for `/llm/vision`.
# - The new endpoint calls interpret_vision() in LLMClient, providing prompt and images.
#
# Steps:
# - Users can call:
#   curl -X POST -H "Content-Type: application/json" -d '{"prompt":"Hello"}' http://localhost:8000/llm/chat_complete
#   curl -X POST -H "Content-Type: application/json" -d '{"prompt":"What is in this image?","images":["<base64>"]}' http://localhost:8000/llm/vision
#
# Integration:
# - Uses LLMClient from llm_client.py
# - If LLM model sizes are changed (like adding :8b/:11b), they are handled in config.yaml and llm_client.py.
#
# Error Handling:
# - If the prompt or images are invalid (ValueError), return HTTP 400.
# - If LLM unreachable (LLMConnectionError), return HTTP 503.
# - If invalid LLM response (LLMResponseError), return HTTP 500.
#
# Future Enhancements:
# - Add parameters like max_tokens, temperature as request fields and pass them to LLMClient.
# - Add streaming responses if needed.
#
###############################################################################

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
from core.llm_client import LLMClient, LLMConnectionError, LLMResponseError

import logging
logger = logging.getLogger(__name__)

router = APIRouter()

###############################################################################
# Request/Response Models
#
# LLMRequest for chat completion:
# - prompt: str (required)
#
# VisionLLMRequest for vision tasks:
# - prompt: str (required)
# - images: list of base64-encoded strings (required)
#
# LLMResponse: 
# - status: "success" on success
# - response: string returned by the LLM
###############################################################################

class LLMRequest(BaseModel):
    prompt: str = Field(..., description="Text prompt for chat completion")

class VisionLLMRequest(BaseModel):
    prompt: str = Field(..., description="Text prompt guiding the vision reasoning")
    images: List[str] = Field(..., description="List of base64-encoded images")

class LLMResponse(BaseModel):
    status: str
    response: str

###############################################################################
# Endpoint: POST /llm/chat_complete
#
# Purpose:
# Respond to textual prompts using the chat model (llama3.1:8b as defined in config).
#
# Steps:
# 1. Validate prompt.
# 2. client = LLMClient()
# 3. result = client.interpret_chat(prompt)
# 4. Return {"status":"success","response":result}
#
# Errors:
# - 400 if prompt empty
# - 503 if LLM unreachable
# - 500 if LLM invalid response
###############################################################################

@router.post("/chat_complete", response_model=LLMResponse)
async def llm_chat_complete(request: LLMRequest):
    prompt = request.prompt.strip()
    logger.info(f"Received chat completion request with prompt: {prompt}")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    client = LLMClient()
    try:
        logger.info(f"Calling interpret_chat with prompt: {prompt}")
        llm_result = client.interpret_chat(prompt)
        return LLMResponse(status="success", response=llm_result)
    except LLMConnectionError as e:
        raise HTTPException(status_code=503, detail=f"LLM service unavailable: {e}")
    except LLMResponseError as e:
        raise HTTPException(status_code=500, detail=f"Invalid LLM response: {e}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}")

###############################################################################
# Endpoint: POST /llm/vision
#
# Purpose:
# Use the vision model (llama3.2-vision:11b) to analyze images with a prompt.
#
# Steps:
# 1. Validate prompt and images (non-empty).
# 2. client = LLMClient()
# 3. result = client.interpret_vision(prompt, images)
# 4. Return {"status":"success","response":result}
#
# Errors:
# - 400 if prompt/images invalid
# - 503 if LLM unreachable
# - 500 if invalid LLM response
###############################################################################

@router.post("/vision", response_model=LLMResponse)
async def llm_vision(request: VisionLLMRequest):
    prompt = request.prompt.strip()
    logger.info(f"Received vision request with prompt: {prompt}")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")
    if not request.images or any(not img.strip() for img in request.images):
        raise HTTPException(status_code=400, detail="Must provide at least one valid base64 image.")

    client = LLMClient()
    try:
        logger.info(f"Calling interpret_vision with prompt: {prompt} and images: {request.images}")
        llm_result = client.interpret_vision(prompt, request.images)
        return LLMResponse(status="success", response=llm_result)
    except LLMConnectionError as e:
        raise HTTPException(status_code=503, detail=f"LLM service unreachable: {e}")
    except LLMResponseError as e:
        raise HTTPException(status_code=500, detail=f"Invalid LLM response: {e}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}")

###############################################################################
# Explanation:
#
# We have now two endpoints:
# - /llm/chat_complete: For text chat completion (8b model).
# - /llm/vision: For vision reasoning (11b model + images).
#
# Both use LLMClient methods interpret_chat and interpret_vision, ensuring we pick 
# the correct sized model as configured in config.yaml.
#
# If we want to ensure model size strictly, we can confirm model name includes ":8b" 
# or ":11b" tags in config.yaml. The LLMClient just uses the model name given; 
# as long as you specify "llama3.1:8b" or "llama3.2-vision:11b" in config.yaml, 
# these routes will call the correct model size without further code changes here.
#
# Future Enhancements:
# - Add optional query parameters for controlling temperature, max_tokens, etc.
# - Add streaming support by changing stream:false to stream:true and making the endpoint return chunks.
#
###############################################################################
