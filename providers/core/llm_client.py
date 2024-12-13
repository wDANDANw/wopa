###############################################################################
# llm_client.py
#
# Revised version: now includes logic to ensure the requested LLM model is present.
# If not present, it tries to pull it using Ollama's REST API (assuming /api/pull).
#
# Changes:
# - _ensure_model_exists(model_name): Checks local models via `GET /api/tags`.
# - If model not found, tries `POST /api/pull` to download it.
#
# Steps now in interpret_chat and interpret_vision:
# 1. Ensure model exists (call _ensure_model_exists).
# 2. If ensured, then proceed with calling /api/generate for actual prompt interpretation.
#
# Note:
# This makes the system more self-contained, as we do not manually run `ollama list` 
# or `ollama pull`. Instead, code relies on Ollama's HTTP endpoints to handle models.
###############################################################################

import requests
from typing import List, Optional
from utils import config_loader

import logging
logger = logging.getLogger(__name__)

class LLMConnectionError(Exception):
    pass

class LLMResponseError(Exception):
    pass

class LLMClient:
    def __init__(self):
        self.config = config_loader.load_config("config.yaml")
        llm_config = self.config.get("llm", {})
        self.global_endpoint = llm_config.get("endpoint", "http://localhost:11434")
        
        models_config = llm_config.get("models", {})

        chat_model_cfg = models_config.get("chat_model", {})
        self.chat_model_name = chat_model_cfg.get("name", "llama3.1:8b")
        self.chat_model_params = chat_model_cfg.get("default_params", {})

        vision_model_cfg = models_config.get("vision_model", {})
        self.vision_model_name = vision_model_cfg.get("name", "llama3.2-vision:11b")
        self.vision_model_params = vision_model_cfg.get("default_params", {})

        self.timeout = llm_config.get("timeout_seconds", 20)

        # TODO: Need to add two "cold start generate instruction to boot up ollama -> load checkpoints, etc."
        # Else almost all requests will timeout
        # Currently manually by 
        # curl http://localhost:11434/api/generate -d '{"model":"llama3.1:8b","prompt":"Hello"}'
        # curl http://localhost:11434/api/generate -d '{"model":"llama3.2-vision:11b","prompt":"What is in this image?","images":["<base64>"]}'


    def interpret_chat(self, prompt: str) -> str:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Prompt must not be empty for interpret_chat().")

        # Ensure chat model exists locally
        logger.info(f"Ensuring chat model '{self.chat_model_name}' exists...")
        self._ensure_model_exists(self.chat_model_name)

        payload = {
            "model": self.chat_model_name,
            "prompt": prompt,
            "stream": False
        }

        if self.chat_model_params:
            payload["options"] = self.chat_model_params

        url = f"{self.global_endpoint}/api/generate"
        data = self._post_request(url, payload)
        response_text = data.get("response")
        if response_text is None:
            raise LLMResponseError("Chat model response missing 'response' field.")
        
        return response_text.strip()

    def interpret_vision(self, prompt: str, images: List[str]) -> str:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Prompt must not be empty for interpret_vision().")

        if not images or any(not img.strip() for img in images):
            raise ValueError("At least one valid base64 image must be provided for vision interpretation.")

        # Ensure vision model exists locally
        self._ensure_model_exists(self.vision_model_name)

        payload = {
            "model": self.vision_model_name,
            "prompt": prompt,
            "stream": False,
            "images": images
        }
        if self.vision_model_params:
            payload["options"] = self.vision_model_params

        url = f"{self.global_endpoint}/api/generate"
        data = self._post_request(url, payload)
        response_text = data.get("response")
        if response_text is None:
            raise LLMResponseError("Vision model response missing 'response' field.")

        return response_text.strip()

    def _ensure_model_exists(self, model_name: str) -> None:
        """
        Check if the given model_name is locally available on Ollama by using GET /api/tags.
        If not found, attempt to pull it via POST /api/pull.
        
        Steps:
        1. Call GET /api/tags
        2. If model_name not in the returned list, call POST /api/pull with model_name.
        3. After pulling, call GET /api/tags again to confirm presence.
        4. If still not found, raise LLMResponseError.
        
        Maintainability:
        - If Ollama changes the API for listing models or pulling models, update these methods.
        - If we want to handle partial downloads or streaming logs from pull, we can parse the streaming response from /api/pull.
        """
        if self._model_in_list(model_name):
            logger.info(f"Model '{model_name}' already exists.")
            return  # Model already exists
        
        # Model not found, try to pull
        logger.info(f"Model '{model_name}' not found, pulling...")
        self._pull_model(model_name)

        # After pulling, check again
        if not self._model_in_list(model_name):
            logger.error(f"Model '{model_name}' not found even after pulling attempt.")
            raise LLMResponseError(f"Model '{model_name}' not found even after pulling attempt.")

    def _model_in_list(self, model_name: str) -> bool:
        """
        Check if the given model_name exists in Ollama's local list by calling GET /api/tags.
        Returns True if found, False otherwise.
        """
        url = f"{self.global_endpoint}/api/tags"
        try:
            r = requests.get(url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            raise LLMConnectionError(f"Failed to connect to LLM at {url}: {e}")

        if r.status_code != 200:
            raise LLMResponseError(f"Failed to list models: {r.status_code}: {r.text}")

        data = r.json()
        models = data.get("models", [])
        # Each model is a dict with "name" key. Example: {"name": "llama3.1"}
        local_names = [m.get("name", "") for m in models]
        # Check if exact model_name matches one in local_names
        return model_name in local_names

    def _pull_model(self, model_name: str) -> None:
        """
        Try to pull the specified model by POST /api/pull with {"model":model_name}.
        If the pulling fails (non-200 response), raise LLMResponseError.
        
        Note: This call may stream responses. The code as written expects a non-streaming response.
        If streaming occurs, we might receive multiple JSON objects. For simplicity, 
        we assume either streaming is disabled or we just wait for final success status.
        
        If we need to handle streaming, we can do line-by-line parsing. For now, 
        we assume a simple final JSON with "status":"success".
        """
        logger.info(f"Pulling model '{model_name}'...")
        url = f"{self.global_endpoint}/api/pull"
        payload = {"model": model_name, "stream": False}
        # If streaming is default, we might have to handle streaming. According 
        # to Ollama docs, "stream":false should give one final response.
        
        try:
            r = requests.post(url, json=payload, timeout=300)  # 5 min timeout to pull large models
            logger.info(f"Model '{model_name}' pulled successfully.")
        except requests.exceptions.RequestException as e:
            raise LLMConnectionError(f"Failed to connect to LLM for pulling model at {url}: {e}")

        if r.status_code != 200:
            # Possibly streaming ended with error
            # If we get a single JSON with error info:
            raise LLMResponseError(f"Failed to pull model '{model_name}': {r.status_code}: {r.text}")

        data = r.json()
        logger.info(f"Model '{model_name}' pull response: {data}")
        # Expect data like {"status":"success"} on success
        if data.get("status") != "success":
            raise LLMResponseError(f"Model pull did not succeed for '{model_name}'. Response: {data}")

    def _post_request(self, url: str, payload: dict) -> dict:
        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            raise LLMConnectionError(f"Failed to connect to LLM at {url}: {e}")

        if r.status_code != 200:
            raise LLMResponseError(f"LLM returned {r.status_code}: {r.text}")

        try:
            data = r.json()
        except ValueError:
            raise LLMResponseError("Invalid JSON response from LLM.")

        return data

###############################################################################
# Explanation:
#
# With these changes, whenever we call interpret_chat or interpret_vision:
# - _ensure_model_exists(model_name) checks if model is locally available via /api/tags.
# - If not found, tries /api/pull to download it.
# - After pulling, checks again. If still not found, raises error.
#
# This way, we don't rely on manual `ollama list` or command-line tools.
# Everything happens via Ollama's REST API inside llm_client.py.
#
# If you see performance overhead, consider caching the "models" list after first check,
# or only pulling once. For initial correctness, this ensures correct model presence.
#
# If model pulling or listing differ from these assumptions, adapt the code accordingly.
###############################################################################
