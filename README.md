# AOAI-call-center-analytics

Call Center Analytics demo. 

**Goal:** automated process of anlysis of incoming recording from call center between customer and agent.

**Orchestration**: Azure Functions automation

## Installation
Deploy to Azure or debug/run locally.

Example of `local.settings.json`:
```JSON
    "AzureWebJobsStorage": "...",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsFeatureFlags": "EnableWorkerIndexing",
    "AZURE_OPENAI_ENDPOINT":"YOUR ENDPOINT",
    "AZURE_OPENAI_KEY":"YOUR KEY",
    "AZURE_OPENAI_MODEL": "YOUR DEPLOYMENT NAME",
    "AZURE_STORAGE_CONNECTION_STRING": "...",
    "AZURE_SPEECH_KEY": "YOUR KEY",
    "AZURE_SPEECH_REGION": "westeurope"
```
> Note: Same variables are expected to be n the Azure Function app as environment variables.


## Acepted format
Recording - MP3, WAV - needs to be dual channel (diarization not needed)

## Process description
1. Transcript
    - Function: `transcript_recording` (blob trigger)
    ```Python
    @app.blob_trigger(arg_name="myblob", path=container_input_recording, connection="AZURE_STORAGE_CONNECTION_STRING") 
    def transcript_recording(myblob: func.InputStream):
    ```
    - Creates transcript from newly arived call recording using Whisper model (Speech Service)
    - Format the transript from Whisper output to output:
        ```
        [100.0] customer: Good morning, Steve.
        [1980.0] agent: Good morning, Katie.
        [3820.0] customer: Have you tried the latest news...
[       ...
        ```
    - Change variable `RECORDING_LANGUAGE` accordingly 

2. Analyze
    - Function: 
    ```Python
    @app.blob_trigger(arg_name="myblob", path=container_input_transcript, connection="AZURE_STORAGE_CONNECTION_STRING")
    def transcript_analysis(myblob: func.InputStream):
    ```
    - Runs call transcript analysis using GPT model
    - Prompt example:
    ```Python
    system_promt = """You are a customer service representative for a company that sells electronics. A customer has called in to inquire about the status of an order. The customer provides the order number and asks for an update. Respond to the customer's inquiry.
    Your task is to assess the call from agent perspective and provide feedback on the agent's performance. You can provide feedback on the agent's tone, empathy, and professionalism. You can also provide suggestions on how the agent can improve their performance.
    Finally, you will give a score to the agent's performance. The score should be between 1 and 5, with 1 being the lowest and 5 being the highest.
    """
    ```

Storage structure:
There are several containers for input, intermediate results and final output of the transcript analysis

1. `container_input_recording` - here should land the recoding
2. `container_output_transcript_tmp` - this is an intermediate result from Whisper transcription
3. `container_input_transcript` - this is an intermediate result from transcriptin formatting, and also serves as trigger for running the analysis
4. `container_output_analysis` - final analysis output, txt/json document

Example:
```Python
container_input_recording = "cc-stage0-input"
container_output_transcript_tmp = "cc-stage0-output"
container_input_transcript = "cc-stage1-transcript"
container_output_analysis = "cc-stage2-transcript-analysis"
```