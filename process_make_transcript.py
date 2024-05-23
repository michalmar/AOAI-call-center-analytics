import requests
import json
import random
import time
from dotenv import load_dotenv, find_dotenv
import os
import logging

load_dotenv(find_dotenv())

headers = {
'Ocp-Apim-Subscription-Key': os.getenv("AZURE_SPEECH_KEY"),
'Content-Type': 'application/json'
}

# generate ranom guid
def random_guid():
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace('x', '%x' % random.randint(0, 15)).replace('y', '%x' % random.randint(8, 11))

def extract_transcription(response):
    response_json = json.loads(response.text)
    payload = {}

    for val in response_json["values"]:
        if "Transcription" in val["kind"]:
            url_resp = val["links"]["contentUrl"]
            break

    # download the transcription file
    response = requests.request("GET", url_resp, headers=headers, data=payload)
    print(response.text)
    return response.text

def save_transcription(text, file_name="transcription.json"):
    # save the transcription file
    with open(file_name, "w") as f:
        f.write(text)
    return file_name

def submit_transcription(file_uri, language="en-us"):
    url = "https://westeurope.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions"

    payload = json.dumps({
    "displayName": f"20240522_{random_guid()}",
    "description": "Speech Studio Batch speech to text",
    "locale": language,
    "contentUrls": [
        file_uri
    ],
    "model": {
        "self": "https://westeurope.api.cognitive.microsoft.com/speechtotext/v3.2-preview.1/models/base/69adf293-9664-4040-932b-02ed16332e00"
    },
    "properties": {
        "wordLevelTimestampsEnabled": False,
        "displayFormWordLevelTimestampsEnabled": False,
        "diarizationEnabled": False,
        "punctuationMode": "DictatedAndAutomatic",
        "profanityFilterMode": "None"
    },
    "customProperties": {}
    })
    response = requests.request("POST", url, headers=headers, data=payload)

    # print(response.text)

    job_url = json.loads(response.text)["links"]["files"]
    return job_url

def poll_transcript(job_url):
    i = 0
    i_max = 15 # max iteration

    while i < i_max:
        payload = {}
        response = requests.request("GET", job_url, headers=headers, data=payload)
        # print(response.text)
        i += 1
        vals = json.loads(response.text)["values"]
        if (len(vals) > 0):
            # transcript = extract_transcription(response)
            # save_transcription(transcript)
            return response
        else:
            print("Running...")
            time.sleep(5)
        
    return None

def main(recording_url, language="en-us"):
    
    job_url = submit_transcription(recording_url, language)
    print(job_url)

    response = poll_transcript(job_url)

    if response is not None:
        transcript = extract_transcription(response)
        # print(transcript)
    else:
        print("No transcript found")
        transcript = None

    return transcript

if __name__ == '__main__':
    recording_url = "https://callcenteranalytics.blob.core.windows.net/cc-stage0-input/katiesteve8.wav"
    main(recording_url)