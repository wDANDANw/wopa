import os
import time
import copy
import torch
import shutil
from PIL import Image, ImageDraw

import base64
import requests

# Removed MobileAgent imports and replaced them with local references
# from .app_worker.api import inference_chat  # Assuming ocr, det from local app_worker modules
from .app_worker.text_localization import ocr
from .app_worker.icon_localization import det
from .app_worker.prompt import get_action_prompt, get_reflect_prompt, get_memory_prompt, get_process_prompt
from .app_worker.chat import init_action_chat, init_reflect_chat, init_memory_chat, add_response, add_response_two_image
from .app_worker.controller import get_screenshot, tap, slide, type, back, home

from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
from modelscope import snapshot_download, AutoModelForCausalLM, AutoTokenizer, GenerationConfig

import concurrent

from worker_definitions.base_worker import BaseWorker

from openai import OpenAI

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

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

class AppWorker(BaseWorker):

    def validate_task(self, task_data: dict):
        """
        Validate input fields 'app_ref' (mandatory) and 'instructions' (optional).
        """
        app_ref = task_data.get("app_ref")
        if not app_ref or not isinstance(app_ref, str) or app_ref.strip() == "":
            return {"error": "missing or empty 'app_ref' field"}
        # instructions optional
        return None

    def process(self, task_data: dict) -> dict:
        instruction = task_data.get("instructions", "No specific instructions.")
        app_ref = task_data["app_ref"]
        base_url = self.config.get("providers_server_url", "http://providers:8003")
        run_duration = self.config.get("app_run_duration", 5)   # minutes
        interval = self.config.get("app_check_interval", 1)     # minutes
        max_total_errors = self.config.get("max_total_errors", 15)
        max_consecutive_errors = self.config.get("max_consecutive_errors", 3)


        steps_data = {
            "Step0_Emulator_Preparation": [],
            "Step1_App_Identification": [],
            "Step2_App_Exploration": []
        }

        # Retry configs
        pre_run_retries = 3
        pre_run_timeout = 120
        run_app_retries = 2
        run_app_timeout = 60

        # Error handling in exploration
        max_total_errors = 15
        max_consecutive_errors = 3
        total_errors = 0
        consecutive_errors = 0

        # Pre-run steps:
        # init_device
        init_result = self._retry_call(lambda: requests.post(f"{base_url}/emulator/init_device", timeout=pre_run_timeout), pre_run_retries, wait=30)
        steps_data["Step0_Emulator_Preparation"].append(self._make_check_entry("check_0_init_device", "emulator_device_init", 0.0, init_result, "Initialize emulator device", pre_run=True))
        if init_result["status"]=="error":
            return self._fail_no_analysis(steps_data, instruction, base_url)
        
        # Need to wait for 20 seconds for emulator to be ready
        logger.info(f"Waiting for 20 seconds for emulator to be ready...")
        time.sleep(20)

        # upload_app if local
        upload_needed = os.path.exists(app_ref)
        if upload_needed:
            def upload_call():
                with open(app_ref,'rb') as f:
                    files = {'file':(os.path.basename(app_ref), f,'application/octet-stream')}
                    return requests.post(f"{base_url}/emulator/upload_app", files=files, timeout=pre_run_timeout)
            upload_result = self._retry_call(upload_call, pre_run_retries, wait=30)
            logger.info(f"Upload result: {upload_result}")
            steps_data["Step0_Emulator_Preparation"].append(self._make_check_entry("check_0_upload_app","emulator_upload_app",0.0,upload_result,"Upload app apk", pre_run=True))
            if upload_result["status"]=="error":
                return self._fail_no_analysis(steps_data, instruction, base_url)
            if "filename" in upload_result.get("data",{}):
                app_ref = upload_result["data"]["filename"]

        # install_app
        def install_call():
            return requests.post(f"{base_url}/emulator/install_app", json={"app_ref":app_ref}, timeout=pre_run_timeout)
        install_result = self._retry_call(install_call, pre_run_retries, wait=30)
        steps_data["Step0_Emulator_Preparation"].append(self._make_check_entry("check_0_install_app","emulator_install_app",0.0,install_result,"Install the app", pre_run=True))
        if install_result["status"]=="error":
            return self._fail_no_analysis(steps_data, instruction, base_url)
        logger.info(f"Install result: {install_result}")


        # Need to wait for 5 seconds for app to be ready
        logger.info(f"Waiting for 5 seconds for app to be ready...")
        time.sleep(5)

        # run_app
        def run_app_call():
            return requests.post(f"{base_url}/emulator/run_app", json={"app_ref":app_ref}, timeout=run_app_timeout)
        run_app_result = self._retry_call(run_app_call, run_app_retries, wait=60)
        logger.info(f"Run app result: task_id: {run_app_result['data']['task_id']}, events: {run_app_result['data']['events']}, status: {run_app_result['data']['status']}")

        steps_data["Step1_App_Identification"].append(self._make_check_entry("check_1_run_app","emulator_run_app",0.0,run_app_result,"Run the app", pre_run=True))
        if run_app_result["status"]=="error":
            return self._fail_no_analysis(steps_data, instruction, base_url)

        emulator_task_id = run_app_result["data"].get("task_id")
        if not emulator_task_id:
            # no task_id means can't proceed
            return self._fail_no_analysis(steps_data, instruction, base_url)

        # initial screenshot
        shot_res = self._get_screenshot_for_task(base_url, emulator_task_id)
        steps_data["Step1_App_Identification"].append(self._make_screenshot_check("check_1_initial_screenshot",0.0,shot_res,"Initial screenshot after run_app"))
        if shot_res["status"]=="error":
            return self._fail_no_analysis(steps_data, instruction, base_url)

        screenshot_path = shot_res["screenshot_path"]

        

        caption_call_method = "api"
        caption_model = "qwen-vl-plus"

        # Additional info
        add_info = "If you want to tap an icon of an app, use the action \"Open app\". If you want to exit an app, use the action \"Home\""

        # Reflection Setting
        reflection_switch = True

        # Memory Setting
        memory_switch = True
        ###################################################################################################
        def generate_local(tokenizer, model, image_file, query):
            query = tokenizer.from_list_format([
                {'image': image_file},
                {'text': query},
            ])
            response, _ = model.chat(tokenizer, query=query, history=None)
            return response

        def get_all_files_in_folder(folder_path):
            file_list = []
            for file_name in os.listdir(folder_path):
                file_list.append(file_name)
            return file_list

        def draw_coordinates_on_image(image_path, coordinates):
            image = Image.open(image_path)
            draw = ImageDraw.Draw(image)
            point_size = 10
            for coord in coordinates:
                draw.ellipse((coord[0] - point_size, coord[1] - point_size, coord[0] + point_size, coord[1] + point_size), fill='red')
            output_image_path = './screenshot/output_image.png'
            image.save(output_image_path)
            return output_image_path


        def crop(image, box, i):
            img = Image.open(image)
            x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
            if x1 >= x2-10 or y1 >= y2-10:
                return
            cropped_image = img.crop((x1, y1, x2, y2))
            # Convert to RGB before saving as JPEG
            if cropped_image.mode == "RGBA":
                cropped_image = cropped_image.convert("RGB")
            cropped_image.save(f"./temp/{i}.jpg")

        def encode_image(image):
            with open(image, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')

        def process_image(image, query):

            b64_image = encode_image(image)

            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": query},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64_image}",
                                }
                            },
                        ],
                    }
                ],
            )
            
            try:
                response = completion.choices[0].message.content
            except:
                response = "This is an icon."
            
            return response


        def generate_api(images, query):
            icon_map = {}
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {executor.submit(process_image, image, query): i for i, image in enumerate(images)}
                
                for future in concurrent.futures.as_completed(futures):
                    i = futures[future]
                    response = future.result()
                    icon_map[i + 1] = response
            
            return icon_map

        def merge_text_blocks(text_list, coordinates_list):
            merged_text_blocks = []
            merged_coordinates = []

            sorted_indices = sorted(range(len(coordinates_list)), key=lambda k: (coordinates_list[k][1], coordinates_list[k][0]))
            sorted_text_list = [text_list[i] for i in sorted_indices]
            sorted_coordinates_list = [coordinates_list[i] for i in sorted_indices]

            num_blocks = len(sorted_text_list)
            merge = [False] * num_blocks

            for i in range(num_blocks):
                if merge[i]:
                    continue
                
                anchor = i
                
                group_text = [sorted_text_list[anchor]]
                group_coordinates = [sorted_coordinates_list[anchor]]

                for j in range(i+1, num_blocks):
                    if merge[j]:
                        continue

                    if abs(sorted_coordinates_list[anchor][0] - sorted_coordinates_list[j][0]) < 10 and \
                    sorted_coordinates_list[j][1] - sorted_coordinates_list[anchor][3] >= -10 and sorted_coordinates_list[j][1] - sorted_coordinates_list[anchor][3] < 30 and \
                    abs(sorted_coordinates_list[anchor][3] - sorted_coordinates_list[anchor][1] - (sorted_coordinates_list[j][3] - sorted_coordinates_list[j][1])) < 10:
                        group_text.append(sorted_text_list[j])
                        group_coordinates.append(sorted_coordinates_list[j])
                        merge[anchor] = True
                        anchor = j
                        merge[anchor] = True

                merged_text = "\n".join(group_text)
                min_x1 = min(group_coordinates, key=lambda x: x[0])[0]
                min_y1 = min(group_coordinates, key=lambda x: x[1])[1]
                max_x2 = max(group_coordinates, key=lambda x: x[2])[2]
                max_y2 = max(group_coordinates, key=lambda x: x[3])[3]

                merged_text_blocks.append(merged_text)
                merged_coordinates.append([min_x1, min_y1, max_x2, max_y2])

            return merged_text_blocks, merged_coordinates
        
        def get_perception_infos(base_url, emulator_task_id, screenshot_file):
            get_screenshot(base_url, emulator_task_id)
            
            width, height = Image.open(screenshot_file).size
            
            text, coordinates = ocr(screenshot_file, ocr_detection, ocr_recognition)
            text, coordinates = merge_text_blocks(text, coordinates)
            
            center_list = [[(coordinate[0]+coordinate[2])/2, (coordinate[1]+coordinate[3])/2] for coordinate in coordinates]
            draw_coordinates_on_image(screenshot_file, center_list)
            
            perception_infos = []
            for i in range(len(coordinates)):
                perception_info = {"text": "text: " + text[i], "coordinates": coordinates[i]}
                perception_infos.append(perception_info)
                
            coordinates = det(screenshot_file, "icon", groundingdino_model)
            
            for i in range(len(coordinates)):
                perception_info = {"text": "icon", "coordinates": coordinates[i]}
                perception_infos.append(perception_info)
                
            image_box = []
            image_id = []
            for i in range(len(perception_infos)):
                if perception_infos[i]['text'] == 'icon':
                    image_box.append(perception_infos[i]['coordinates'])
                    image_id.append(i)

            for i in range(len(image_box)):
                crop(screenshot_file, image_box[i], image_id[i])

            images = get_all_files_in_folder(temp_file)
            if len(images) > 0:
                images = sorted(images, key=lambda x: int(x.split('/')[-1].split('.')[0]))
                image_id = [int(image.split('/')[-1].split('.')[0]) for image in images]
                icon_map = {}
                prompt = 'This image is an icon from a phone screen. Please briefly describe the shape and color of this icon in one sentence.'
                if caption_call_method == "local":
                    for i in range(len(images)):
                        image_path = os.path.join(temp_file, images[i])
                        icon_width, icon_height = Image.open(image_path).size
                        if icon_height > 0.8 * height or icon_width * icon_height > 0.2 * width * height:
                            des = "None"
                        else:
                            des = generate_local(tokenizer, model, image_path, prompt)
                        icon_map[i+1] = des
                else:
                    for i in range(len(images)):
                        images[i] = os.path.join(temp_file, images[i])
                    icon_map = generate_api(images, prompt)
                for i, j in zip(image_id, range(1, len(image_id)+1)):
                    if icon_map.get(j):
                        perception_infos[i]['text'] = "icon: " + icon_map[j]

            for i in range(len(perception_infos)):
                perception_infos[i]['coordinates'] = [int((perception_infos[i]['coordinates'][0]+perception_infos[i]['coordinates'][2])/2), int((perception_infos[i]['coordinates'][1]+perception_infos[i]['coordinates'][3])/2)]
                
            return perception_infos, width, height

        ### Load caption model ###
        device = "cuda"
        torch.manual_seed(1234)
        if caption_call_method == "local":
            if caption_model == "qwen-vl-chat":
                model_dir = snapshot_download('qwen/Qwen-VL-Chat', revision='v1.1.0')
                model = AutoModelForCausalLM.from_pretrained(model_dir, device_map=device, trust_remote_code=True).eval()
                model.generation_config = GenerationConfig.from_pretrained(model_dir, trust_remote_code=True)
            elif caption_model == "qwen-vl-chat-int4":
                qwen_dir = snapshot_download("qwen/Qwen-VL-Chat-Int4", revision='v1.0.0')
                model = AutoModelForCausalLM.from_pretrained(qwen_dir, device_map=device, trust_remote_code=True,use_safetensors=True).eval()
                model.generation_config = GenerationConfig.from_pretrained(qwen_dir, trust_remote_code=True, do_sample=False)
            else:
                print("If you choose local caption method, you must choose the caption model from \"Qwen-vl-chat\" and \"Qwen-vl-chat-int4\"")
                exit(0)
            tokenizer = AutoTokenizer.from_pretrained(qwen_dir, trust_remote_code=True)
        elif caption_call_method == "api":
            pass
        else:
            print("You must choose the caption model call function from \"local\" and \"api\"")
            exit(0)


        ### Load ocr and icon detection model ###
        groundingdino_dir = snapshot_download('AI-ModelScope/GroundingDINO', revision='v1.0.0')
        groundingdino_model = pipeline('grounding-dino-task', model=groundingdino_dir)
        ocr_detection = pipeline(Tasks.ocr_detection, model='damo/cv_resnet18_ocr-detection-line-level_damo')
        ocr_recognition = pipeline(Tasks.ocr_recognition, model='damo/cv_convnextTiny_ocr-recognition-document_damo')


        thought_history = []
        summary_history = []
        action_history = []
        summary = ""
        action = ""
        completed_requirements = ""
        memory = ""
        insight = ""
        temp_file = "temp"
        screenshot = "screenshot"
        if not os.path.exists(temp_file):
            os.mkdir(temp_file)
        else:
            shutil.rmtree(temp_file)
            os.mkdir(temp_file)
        if not os.path.exists(screenshot):
            os.mkdir(screenshot)
        error_flag = False


        iter = 0
        while True:
            iter += 1
            if iter == 1:
                screenshot_file = "./screenshot/screenshot.jpg"
                perception_infos, width, height = get_perception_infos(base_url, emulator_task_id, screenshot_file)
                shutil.rmtree(temp_file)
                os.mkdir(temp_file)
                
                keyboard = False
                keyboard_height_limit = 0.9 * height
                for perception_info in perception_infos:
                    if perception_info['coordinates'][1] < keyboard_height_limit:
                        continue
                    if 'ADB Keyboard' in perception_info['text']:
                        keyboard = True
                        break

            prompt_action = get_action_prompt(instruction, perception_infos, width, height, keyboard, summary_history, action_history, summary, action, add_info, error_flag, completed_requirements, memory)
            chat_action = init_action_chat()
            chat_action = add_response("user", prompt_action, chat_action, screenshot_file)

            output_action = inference_chat(chat_action)
            thought = output_action.split("### Thought ###")[-1].split("### Action ###")[0].replace("\n", " ").replace(":", "").replace("  ", " ").strip()
            summary = output_action.split("### Operation ###")[-1].replace("\n", " ").replace("  ", " ").strip()
            action = output_action.split("### Action ###")[-1].split("### Operation ###")[0].replace("\n", " ").replace("  ", " ").strip()
            chat_action = add_response("assistant", output_action, chat_action)
            status = "#" * 50 + " Decision " + "#" * 50
            print(status)
            print(output_action)
            print('#' * len(status))
            
            if memory_switch:
                prompt_memory = get_memory_prompt(insight)
                chat_action = add_response("user", prompt_memory, chat_action)
                output_memory = inference_chat(chat_action)
                chat_action = add_response("assistant", output_memory, chat_action)
                status = "#" * 50 + " Memory " + "#" * 50
                print(status)
                print(output_memory)
                print('#' * len(status))
                output_memory = output_memory.split("### Important content ###")[-1].split("\n\n")[0].strip() + "\n"
                if "None" not in output_memory and output_memory not in memory:
                    memory += output_memory
            
            if "Open app" in action:
                app_name = action.split("(")[-1].split(")")[0]
                text, coordinate = ocr(screenshot_file, ocr_detection, ocr_recognition)
                tap_coordinate = [0, 0]
                for ti in range(len(text)):
                    if app_name == text[ti]:
                        name_coordinate = [int((coordinate[ti][0] + coordinate[ti][2])/2), int((coordinate[ti][1] + coordinate[ti][3])/2)]
                        tap(base_url, emulator_task_id, name_coordinate[0], name_coordinate[1]- int(coordinate[ti][3] - coordinate[ti][1]))# 
                        break
            
            elif "Tap" in action:
                coordinate = action.split("(")[-1].split(")")[0].split(", ")
                x, y = int(coordinate[0]), int(coordinate[1])
                tap(base_url, emulator_task_id, x, y)
            
            elif "Swipe" in action:
                coordinate1 = action.split("Swipe (")[-1].split("), (")[0].split(", ")
                coordinate2 = action.split("), (")[-1].split(")")[0].split(", ")
                x1, y1 = int(coordinate1[0]), int(coordinate1[1])
                x2, y2 = int(coordinate2[0]), int(coordinate2[1])
                slide(base_url, emulator_task_id, x1, y1, x2, y2)
                
            elif "Type" in action:
                if "(text)" not in action:
                    text = action.split("(")[-1].split(")")[0]
                else:
                    text = action.split(" \"")[-1].split("\"")[0]
                type(base_url, emulator_task_id, text)
            
            elif "Back" in action:
                back(base_url, emulator_task_id)
            
            elif "Home" in action:
                home(base_url, emulator_task_id)
                
            elif "Stop" in action:
                break
            
            time.sleep(5)
            
            last_perception_infos = copy.deepcopy(perception_infos)
            last_screenshot_file = "./screenshot/last_screenshot.jpg"
            last_keyboard = keyboard
            if os.path.exists(last_screenshot_file):
                os.remove(last_screenshot_file)
            os.rename(screenshot_file, last_screenshot_file)
            
            perception_infos, width, height = get_perception_infos(base_url, emulator_task_id, screenshot_file)
            shutil.rmtree(temp_file)
            os.mkdir(temp_file)
            
            keyboard = False
            for perception_info in perception_infos:
                if perception_info['coordinates'][1] < keyboard_height_limit:
                    continue
                if 'ADB Keyboard' in perception_info['text']:
                    keyboard = True
                    break
            
            if reflection_switch:
                prompt_reflect = get_reflect_prompt(instruction, last_perception_infos, perception_infos, width, height, last_keyboard, keyboard, summary, action, add_info)
                chat_reflect = init_reflect_chat()
                chat_reflect = add_response_two_image("user", prompt_reflect, chat_reflect, [last_screenshot_file, screenshot_file])

                output_reflect = inference_chat(chat_reflect)
                reflect = output_reflect.split("### Answer ###")[-1].replace("\n", " ").strip()
                chat_reflect = add_response("assistant", output_reflect, chat_reflect)
                status = "#" * 50 + " Reflcetion " + "#" * 50
                print(status)
                print(output_reflect)
                print('#' * len(status))
            
                if 'A' in reflect:
                    thought_history.append(thought)
                    summary_history.append(summary)
                    action_history.append(action)
                    
                    prompt_planning = get_process_prompt(instruction, thought_history, summary_history, action_history, completed_requirements, add_info)
                    chat_planning = init_memory_chat()
                    chat_planning = add_response("user", prompt_planning, chat_planning)
                    output_planning = inference_chat(chat_planning)
                    chat_planning = add_response("assistant", output_planning, chat_planning)
                    status = "#" * 50 + " Planning " + "#" * 50
                    print(status)
                    print(output_planning)
                    print('#' * len(status))
                    completed_requirements = output_planning.split("### Completed contents ###")[-1].replace("\n", " ").strip()
                    
                    error_flag = False
                
                elif 'B' in reflect:
                    error_flag = True
                    back(base_url, emulator_task_id)
                    
                elif 'C' in reflect:
                    error_flag = True
            
            else:
                thought_history.append(thought)
                summary_history.append(summary)
                action_history.append(action)
                
                prompt_planning = get_process_prompt(instruction, thought_history, summary_history, action_history, completed_requirements, add_info)
                chat_planning = init_memory_chat()
                chat_planning = add_response("user", prompt_planning, chat_planning)
                output_planning = inference_chat(chat_planning)
                chat_planning = add_response("assistant", output_planning, chat_planning)
                status = "#" * 50 + " Planning " + "#" * 50
                print(status)
                print(output_planning)
                print('#' * len(status))
                completed_requirements = output_planning.split("### Completed contents ###")[-1].replace("\n", " ").strip()
                
            os.remove(last_screenshot_file)

        ##################################################################################################
        # ORIGINAL run.py CODE ENDS HERE
        ##################################################################################################

        # After finishing the process loop:
        return {"status":"completed","result":{"message":"Done"}}

    
    def _fail_no_analysis(self, steps_data, instructions, base_url):
        # If we fail pre-run or run, no analysis done => final aggregator with minimal result?
        # Just produce a final minimal JSON: risk=high (unknown)
        # aggregator not needed
        minimal = {
            "status":"completed",
            "result":{
                "risk_level":"high",
                "confidence":0.5,
                "reasons":{
                    "Step0_Emulator_Preparation":steps_data["Step0_Emulator_Preparation"],
                    "Step1_App_Identification":steps_data["Step1_App_Identification"],
                    "Step2_App_Exploration":steps_data["Step2_App_Exploration"]
                }
            }
        }
        return minimal
    
    def _get_screenshot_for_task(self, base_url, task_id):
        try:
            resp = requests.get(f"{base_url}/emulator/screenshot", params={"task_id":task_id}, timeout=30)
            if resp.status_code != 200:
                return {"status":"error","message":f"screenshot {resp.status_code}"}
            data = resp.json()
            if data.get("status")!="ok":
                return {"status":"error","message":"screenshot not ok"}
            b64_str = data.get("screenshot","")
            if not b64_str:
                return {"status":"error","message":"No screenshot data"}
            screenshot_path = "./app_worker_screenshot.jpg"
            with open(screenshot_path,"wb") as f:
                f.write(base64.b64decode(b64_str))
            return {"status":"completed","screenshot_path":screenshot_path}
        except requests.RequestException as e:
            return {"status":"error","message":f"Net error screenshot: {str(e)}"}

    def _retry_call(self, func, max_retries, wait=10):
        for i in range(max_retries):
            try:
                resp = func()
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") in ["ok","success"]:
                        return {"status":"completed","data":data}
                    else:
                        # Not ok
                        pass
                else:
                    # non-200
                    pass
            except requests.RequestException:
                pass
            if i<max_retries-1:
                time.sleep(wait)
        return {"status":"error","message":"Max retries exceeded"}

    def _make_check_entry(self, check_id, agent, weight, result, explanation, pre_run=False):
        # If error in pre-run or run steps doesn't affect suspicious rating (no suspicious from these steps)
        risk = "low"
        conf = 0.8 if result["status"]=="completed" else 0.5
        explan = explanation
        if result["status"]=="completed":
            explan+=" - success."
        else:
            explan+=f" - {result.get('message','failed')}"
        return {
            "check_id":check_id,
            "analysis_agent":agent,
            "weight":weight,
            "risk_level":risk,
            "confidence":conf,
            "explanation":explan
        }
    
    def _make_screenshot_check(self, check_id, weight, result, explanation):
        if result["status"]=="error":
            return {
                "check_id":check_id,
                "analysis_agent":"emulator_screenshot",
                "weight":weight,
                "risk_level":"low",
                "confidence":0.5,
                "explanation":f"{explanation} - {result.get('message','no message')}"
            }
        else:
            return {
                "check_id":check_id,
                "analysis_agent":"emulator_screenshot",
                "weight":weight,
                "risk_level":"low",
                "confidence":0.7,
                "explanation":f"{explanation} - Screenshot taken."
            }