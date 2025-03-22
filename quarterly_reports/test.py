
import google.generativeai as genai
client = genai.Client(api_key='AIzaSyDdDYOFwnK0Xg993XxfIejd_WEYwgtWsWI')
response = client.models.generate_content(
    model='gemini-2.0-flash', contents='How does RLHF work?'
)
print(response.text)