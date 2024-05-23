import json
import os
from dotenv import load_dotenv
import argparse
import os
from openai import AzureOpenAI


load_dotenv()

def process_transcript(transcript_file):
    transcript = transcript_file.read()
    
    result = do_semantic_analysis(transcript)
    return result
    

def do_semantic_analysis(transcript):
    client = AzureOpenAI(
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"), 
    api_key=os.getenv("AZURE_OPENAI_KEY"),  
    api_version="2024-02-15-preview"
    )
    system_promt = """You are a customer service representative for a company that sells electronics. A customer has called in to inquire about the status of an order. The customer provides the order number and asks for an update. Respond to the customer's inquiry.
    Your task is to assess the call from agent perspective and provide feedback on the agent's performance. You can provide feedback on the agent's tone, empathy, and professionalism. You can also provide suggestions on how the agent can improve their performance.
    Finally, you will give a score to the agent's performance. The score should be between 1 and 5, with 1 being the lowest and 5 being the highest.
    """
    message_text = [{"role":"system","content": system_promt}]

    content = f"{transcript}"

    message_text.append({"role":"user","content":content})

    completion = client.chat.completions.create(
    model=os.getenv("AZURE_OPENAI_MODEL"), # model = "deployment_name"
    messages = message_text,
    temperature=0.25,
    max_tokens=4000,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
    stop=None
    )


    #print(completion.choices[0].message.content)

    response = completion.choices[0].message.content

    return response

def main(transcript_folder):
    file_count = 0

    folder_output = f'{transcript_folder}-semantic_analysis-out'
    # create folder for responses
    if not os.path.exists(folder_output):
        os.makedirs(folder_output)

    # go through all files in the folder
    for filename in os.listdir(transcript_folder):
        if filename.endswith(".json"):
            file_count += 1
            transcript_file = os.path.join(transcript_folder, filename)
            print(f"Processing {transcript_file}")
            # transcript_file = 'transcript.json'
            transcript  = process_transcript(transcript_file)

            response_json = do_semantic_analysis(transcript)

            with open(os.path.join(folder_output,f'{filename}-response.json'), 'w', encoding="utf-8") as f:
                f.write(response_json)
    
    print(f"Processed {file_count} files")


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Process a transcript file.')
    parser.add_argument('-f', '--foldername', type=str, required=True, help='The name of the folder where transcript files are located')

    args = parser.parse_args()

    main(args.foldername)
