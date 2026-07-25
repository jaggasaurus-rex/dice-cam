import ollama
import cv2

#image_test = r"C:\test\testdice.jpg"
feed = cv2.VideoCapture(0)
ret, frame = feed.read()
success, buffer = cv2.imencode('.jpg', frame)
image_jpg = buffer.tobytes()

def ollamaCall():
    response = ollama.generate(
        model="qwen2.5vl:3b",
        prompt="What number is displayed on the top of the die? Reply with only the number.",
        images=[image_jpg],
        )

    print(response.response)

ollamaCall()
