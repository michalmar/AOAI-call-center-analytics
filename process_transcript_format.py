import json
import os
from dotenv import load_dotenv
import argparse
import os
from openai import AzureOpenAI


load_dotenv()

def process_transcript(transcript_file):
    transcript = transcript_file.read()
    transcript = json.loads(transcript)
    
    #with open(transcript_file, 'r', encoding="utf-8") as f:
        #transcript = json.load(f)
    # return transcript

    # # def main():
    # transcript_file = 'transcript.json'
    # transcript = process_transcript(transcript_file  = transcript_file)

    # # if __name__ == '__main__':
    # #     main()


    recognizedPhrases = transcript["recognizedPhrases"]


    for phrase in recognizedPhrases:
        # Access each key-value pair in the JSON object
        # for key, value in phrase.items():
        #     print(f"{key}: {value}")
        # del phrase["nBest"]
        del phrase["offset"]
        del phrase["duration"]
        phrase["text"] = phrase["nBest"][0]["display"]
        del phrase["nBest"]
        phrase["person"] = "agent" if phrase["channel"] == 1 else "customer"
        phrase["offsetInTicks"] = phrase["offsetInTicks"] / 10000

    # Assuming recognizedPhrases is your list of dictionaries
    recognizedPhrases = sorted(recognizedPhrases, key=lambda x: x['offsetInTicks'])

    transcript_plain_text = "" 
    for phrase in recognizedPhrases:
       # print(f'[{phrase["offsetInTicks"]}] {phrase["person"]}: {phrase["text"]}')
        transcript_plain_text += f'[{phrase["offsetInTicks"]}] {phrase["person"]}: {phrase["text"]}\n'
    
    #with open("out.json", 'w', encoding="utf-8") as f:
        #f.write(transcript_plain_text)
        
    return transcript_plain_text



def main(transcript_folder):
    file_count = 0

    folder_output = f'{transcript_folder}-format-out'
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

            

            with open(os.path.join(folder_output,f'{filename}-response.json'), 'w', encoding="utf-8") as f:
                f.write(transcript)
    
    print(f"Processed {file_count} files")


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Process a transcript file.')
    parser.add_argument('-f', '--foldername', type=str, required=True, help='The name of the folder where transcript files are located')

    args = parser.parse_args()

    main(args.foldername)
