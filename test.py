import google.generativeai as genai
import pyaudio
from dotenv import load_dotenv

load_dotenv()

genai.configure()

model = genai.GenerativeModel('gemini-2.0-flash')

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024)

print("Listening...")

upload = genai.upload_file(path=r'uploaded_audio\From_Simple_Compression_to_Cutting-Edge_AI__The_Evolutionary_Jo.mp3')

while True:
    audio_data = stream.read(1024)

    response = model.generate_content(
        contents=upload
    )

    print(response.text)

