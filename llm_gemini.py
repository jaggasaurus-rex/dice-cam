from google import genai
from google.genai import types
from google.genai import errors
from internal_variables import *
import glob
from pathlib import Path
import ai_variables as av
from general_variables import ai_location, ai_project_name, ai_thinking_budget, ai_model

class DieReadError(Exception):
    pass

config = types.GenerateContentConfig(
    system_instruction=av.system_instruction_var,
    temperature=av.temperature_var,
    max_output_tokens=av.max_output_tokens_var,
    response_mime_type=av.response_mime_type_var,
    response_schema=av.response_schema_var,
    thinking_config=types.ThinkingConfig(thinking_budget=ai_thinking_budget)
)

sixnine_config = types.GenerateContentConfig(
    system_instructions=av.sixnine_instruction_var,
    temperature=av.temperature_var,
    max_output_tokens=av.max_output_tokens_var,
    response_mime_type=av.response_mime_type_var,
    response_schema=av.SixNineReading,
    thinking_config=types.ThinkingConfig(thinking_budget=ai_thinking_budget),
)

client = genai.Client(
    vertexai=True,
    project=ai_project_name,
    location=ai_location,
)

def readDie(path):
    part = types.Part.from_bytes(
        data=Path(path).read_bytes(),
        mime_type="image/png"
    )

    try:
        response = client.models.generate_content(
                model=ai_model,
                contents=[part, "Read the top face of this d20."],
                config=config
            )
        if not response.candidates:
            return None
        if response.candidates[0].finish_reason != types.FinishReason.STOP:
            print(response.candidates[0].finish_reason)
            return None
        value = response.parsed
        return value

    except errors.ClientError as e:
        if e.code == 429 and "PerDay" in str(e):
            raise DieReadError("Daily quota exhausted, your AI can't function without usage credits") from e
        elif e.code == 429 and "PerDay" not in str(e):
            raise DieReadError("Temporarily unable to call AI. Please try again.") from e
        elif e.code == 404:
            raise DieReadError("Error: Cannot access the selected AI model") from e
        elif e.code == 503:
            raise DieReadError("AI model is busy right now and can't return a response") from e
        raise
    except errors.APIError as e:
        raise

def sixNineSubagent(path, top_face_position, model=ai_model):
    part = types.Part.from_bytes(
        data=Path(path).read_bytes(),
        mime_type="image/png"
    )

    prompt = (f"The top face was located as follows: {top_face_position}\n"
              f"Decide whether that face shows a 6 or a 9")

    try:
        response = client.models.generate_content(
                model=model,
                contents=[part, prompt],
                config=sixnine_config
            )
        if not response.candidates:
            return None
        if response.candidates[0].finish_reason != types.FinishReason.STOP:
            print(f"{path}: sixnine finish_reason={response.candidates[0].finish_reason}")
            return None
        value = response.parsed
        return value

    except errors.ClientError as e:
        if e.code == 429 and "PerDay" in str(e):
            raise DieReadError("Daily quota exhausted, your AI can't function without usage credits") from e
        elif e.code == 429 and "PerDay" not in str(e):
            raise DieReadError("Temporarily unable to call AI. Please try again.") from e
        elif e.code == 404:
            raise DieReadError("Error: Cannot access the selected AI model") from e
        elif e.code == 503:
            raise DieReadError("AI model is busy right now and can't return a response") from e
        raise
    except errors.APIError as e:
        raise

def opposite_face_valid(reading):
    if reading.value is None:
        return True
    opposite_face = 21 - reading.value
    if opposite_face not in reading.other_face_numerals:
        return True
    return False
    
    

def testCase():
    for path in sorted(glob.glob("captures/*.png")):
        try: 
            response = readDie(path)
        except DieReadError as e:
            print(path, e)
            continue
        if response is None:
            print(path, "no reading")
            continue

        print(response.value, response.other_face_numerals, opposite_face_valid(response))
