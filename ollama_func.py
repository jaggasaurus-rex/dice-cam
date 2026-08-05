import ollama
import cv2
import glob
from general_variables import upscale_val

#image_test = r"C:\test\testdice.jpg"
#feed = cv2.VideoCapture(0)
#ret, frame = feed.read()
#success, buffer = cv2.imencode('.jpg', frame)
#image_jpg = buffer.tobytes()

image_test = r"C:\Users\Tyler\Documents\Coding Projects\BootDev\dice-cam\captures\roll_20260804_184541.png"

def ollamaCall(image_array):
    upscaled = cv2.resize(image_array, None, fx=upscale_val, fy=upscale_val, interpolation=cv2.INTER_CUBIC)
    success, buffer = cv2.imencode('.jpg', upscaled)
    response = ollama.generate(
        model="qwen2.5vl:7b",
        prompt="What number is displayed on the top of the die? Only count the very top number, nothing at an angle. Reply with only the number. If you cannot identify the number reply UNKNOWN",
        images=[buffer.tobytes()],
        )

    return (response.response)

def testCase():

    for path in sorted(glob.glob("captures/*.png")):
        img = cv2.imread(path)
    
        response = ollamaCall(img)
        
        try:
            value = int(response.strip())
        except ValueError:
            value = None #abstain

        print(value)

testCase()
        