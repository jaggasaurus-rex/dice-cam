from pydantic import BaseModel
from typing import Optional, Literal


class DieReading(BaseModel):
    value: Optional[int]
    confidence: Literal["high", "medium", "low"]


system_instruction_var = """
You are reading 20-sided dice from a cropped photograph.
Report the number printed on the face directly facing the camera, in the center of the die.
The numeral may appear at any rotation.
If there are multiple dice, sum the values of the dice before reporting.
If you cannot read any of the dice with confidence, set value to null.
Never guess a number to fill the field.
"""
temperature_var = 0.0
max_output_tokens_var = 1200
response_mime_type_var = "application/json"
response_schema_var = DieReading
