import ollama
import cv2

#image_test = r"C:\test\testdice.jpg"
#feed = cv2.VideoCapture(0)
#ret, frame = feed.read()
#success, buffer = cv2.imencode('.jpg', frame)
#image_jpg = buffer.tobytes()

def ollamaCall(image_jpg):
    response = ollama.generate(
        model="qwen2.5vl:7b",
        prompt="What number is displayed on the top of the die? Only count the very top number, nothing at an angle. If it's a non-number symbol reply 20. Reply with only the number.",
        images=[image_jpg],
        )

    return (response.response)

