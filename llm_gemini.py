from google import genai
from google.genai import types
from google.genai import errors
from internal_variables import *
import glob
from pathlib import Path
import ai_variables as av
from general_variables import ai_location, ai_project_name


config = types.GenerateContentConfig(
    system_instruction=av.system_instruction_var,
    temperature=av.temperature_var,
    max_output_tokens=av.max_output_tokens_var,
    response_mime_type=av.response_mime_type_var,
    response_schema=av.response_schema_var,
    thinking_config=types.ThinkingConfig(thinking_budget=512)
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
                model="gemini-2.5-flash",
                contents=[part, "Read the top face of this d20."],
                config=config
            )
        value = response.parsed
        return value

    except errors.ClientError as e:
        if e.code == 429 and "PerDay" in str(e):
            return f"Daily quota exhausted, your AI can't function without usage credits"
        elif e.code == 429 and "PerDay" not in str(e):
            return f"Temporarily unable to call AI. Please try again."
        elif e.code == 404:
            return f"Error: Cannot access the selected AI model"
        elif e.code == 503:
            return f"AI model is busy right now and can't return a response"
        raise


    
    

def testCase():

    for path in sorted(glob.glob("captures/*.png")):
        response = readDie(path)

        print(response)

#testCase()