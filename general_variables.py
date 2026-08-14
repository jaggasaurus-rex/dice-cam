error_margin = 2
roll_dwell = 2.0
occupancy_threshold = 2000
partial_occupancy_min = 200
outlier_occupancy = 8000
crop_pad = 10
upscale_val = 2
sharpness_floor = 40

#frame initialization
min_aspect = 0.7
max_aspect = 1.4

#camera
max_focus_value = 255

#capture_generator
coarse_sweep_step_size = 20
fine_sweep_step_size = 5
die_id = "dark_red"

#ai variables
ai_project_name = "dice-cam"
ai_location = "global"
ai_thinking_budget = 2049 
ai_model = "gemini-3.5-flash"
ai_output_tokens = 8196


"""
Config: gemini-3.5-flash, thinking_budget=2096, 
max_output_tokens=8196, crop with pad_ratio=0.5, 
upscale, specialist off. Baseline 45/53 on the skewed set, 
~94% weighted to real rolls, first pass reproducible run-to-run.
"""