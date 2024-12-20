import base64
import requests
from openai import OpenAI
import os

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

API_KEY = os.environ.get("OPENAI_API_KEY")  # Ensure this is set in your environment
if not API_KEY:
    logger.warning("No OPENAI_API_KEY found in environment! Please set it.")
client = OpenAI(api_key=API_KEY)

def inference_chat(chat):
    """
    Unified inference call to OpenAI GPT-4o model.
    messages: list of dict like [{"role":"system","content":"..."},{"role":"user","content":"..."}]
    """

    messages = []

    for role, content in chat:
        messages.append({"role": role, "content": content})

    # Using the updated OpenAI code snippet:
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    return completion.choices[0].message.content


# def inference_chat(chat, model, api_url, token):    
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {token}"
#     }

#     data = {
#         "model": model,
#         "messages": [],
#         "max_tokens": 2048,
#         'temperature': 0.0,
#         "seed": 1234
#     }

#     for role, content in chat:
#         data["messages"].append({"role": role, "content": content})

#     while True:
#         try:
#             res = requests.post(api_url, headers=headers, json=data)
#             res_json = res.json()
#             res_content = res_json['choices'][0]['message']['content']
#         except:
#             print("Network Error:")
#             try:
#                 print(res.json())
#             except:
#                 print("Request Failed")
#         else:
#             break
    
#     return res_content