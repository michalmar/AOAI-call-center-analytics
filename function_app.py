import azure.functions as func
import logging
from azure.storage.blob import BlobClient, ContentSettings
import io
import os
import re
from process_transcript_format import process_transcript as process_transcript_format_main
from process_transcript_semantic_analysis import process_transcript as process_transcript_analysis
from process_make_transcript import main as process_make_transcript

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

content_settings = ContentSettings(content_type='application/json')


container_input_recording = "cc-stage0-input"
container_output_transcript_tmp = "cc-stage0-output"
container_input_transcript = "cc-stage1-transcript"
container_output_analysis = "cc-stage2-transcript-analysis"
RECORDING_LANGUAGE = "en-us"

def get_file_name(blob_name):
    return blob_name.split('/')[-1]

def extract_url_from_connstr(conn_str):
    account_match = re.search(r'AccountName=([^;]*)', conn_str)
    suffix_match = re.search(r'EndpointSuffix=([^;]*)', conn_str)

    account_name = account_match.group(1) if account_match else None
    endpoint_suffix = suffix_match.group(1) if suffix_match else None

    return f"https://{account_name}.blob.{endpoint_suffix}/"


@app.blob_trigger(arg_name="myblob", path=container_input_recording, connection="AZURE_STORAGE_CONNECTION_STRING") 
def transcript_recording(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {myblob.length} bytes")
    
    file_url = f"{extract_url_from_connstr(AZURE_STORAGE_CONNECTION_STRING)}{myblob.name}"

    # file_url = file_url.replace("//","/")

    logging.info(f"Recording URL: {file_url}")

    # call Whisper model for transcription
    transcript = process_make_transcript(file_url, RECORDING_LANGUAGE)

    logging.info(f"Transcript created.")

    # Convert string to bytes
    byte_data = transcript.encode('utf-8')

    # Create a BytesIO object and write the byte data to it
    blob = io.BytesIO(byte_data)

    # Upload data on Blob
    _file_name = get_file_name(myblob.name)
    logging.info(f"Transcript generated into: {_file_name} file.")   
    blob_client = BlobClient.from_connection_string(conn_str=AZURE_STORAGE_CONNECTION_STRING, container_name=container_output_transcript_tmp, blob_name=_file_name)
    blob_client.upload_blob(byte_data, content_settings=content_settings, overwrite=True)
    blob_client.close()

    # format the transcript from Whisper output to cust x agent format
    string_data = process_transcript_format_main(blob)
    
    # Convert string to bytes
    byte_data = string_data.encode('utf-8')

    # Create a BytesIO object and write the byte data to it
    #blob = io.BytesIO(byte_data)

    # Upload data on Blob
    _file_name = get_file_name(myblob.name) + ".json"
    logging.info(f"Transcript generated into: {_file_name} file.")   
    blob_client = BlobClient.from_connection_string(conn_str=AZURE_STORAGE_CONNECTION_STRING, container_name=container_input_transcript, blob_name=_file_name)
    blob_client.upload_blob(byte_data, content_settings=content_settings, overwrite=True)
    blob_client.close()

@app.blob_trigger(arg_name="myblob", path=container_input_transcript, connection="AZURE_STORAGE_CONNECTION_STRING")
def transcript_analysis(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {myblob.length} bytes")
    
    if myblob.name.endswith(".json"):
        string_data = process_transcript_analysis(myblob)
    
        # Convert string to bytes
        byte_data = string_data.encode('utf-8')

        # Create a BytesIO object and write the byte data to it
        #blob = io.BytesIO(byte_data)

        # Upload data on Blob
        _file_name = get_file_name(myblob.name)
        logging.info(f"Transcript analysed. Output file: {_file_name} file.")
        blob_client = BlobClient.from_connection_string(conn_str=AZURE_STORAGE_CONNECTION_STRING, container_name=container_output_analysis, blob_name=_file_name)
        blob_client.upload_blob(byte_data, content_settings=content_settings, overwrite=True)
        blob_client.close()
    else:
        logging.info(f"No file !")


