import azure.functions as func
import logging
from azure.storage.blob import BlobClient, ContentSettings
import io
import os
import re
from process_transcript_format import process_transcript as process_transcript_format_main
from process_transcript_semantic_analysis import process_transcript as process_transcript_analysis
from process_make_transcript import main as process_make_transcript

from sample_figure_understanding import analyze_layout as analyze_layout
import uuid
import shutil

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

content_settings = ContentSettings(content_type='application/json')


container_input_recording = "cc-stage0-input"
container_output_transcript_tmp = "cc-stage0-output"
container_input_transcript = "cc-stage1-transcript"
container_output_analysis = "cc-stage2-transcript-analysis"
RECORDING_LANGUAGE = "en-us"

temp_path = os.getenv('TMPDIR', '/tmp')
logging.warn(f"Temp path: {temp_path}")

def get_file_name(blob_name):
    return blob_name.split('/')[-1]

def extract_url_from_connstr(conn_str):
    conn_str = "DefaultEndpointsProtocol=https;AccountName=callcenteranalytics;AccountKey=D2b8idXOAfucZbY7Labwwc7HKcwxcE/Y4odHS9tVUUd7dYnvxqfnXJS6Hoxc9i2CKtt3SaDwMwS1+ASttj9OLQ==;EndpointSuffix=core.windows.net"
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




AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME_IMAGES = os.getenv("AZURE_STORAGE_CONTAINER_NAME_IMAGES")
AZURE_STORAGE_CONTAINER_NAME_DOCS = os.getenv("AZURE_STORAGE_CONTAINER_NAME_DOCS")

AZURE_STORAGE_CONTAINER_NAME_INPUT = "doc-in-docs"

def create_folder(tmp_path, folder_name=""):
    folder_path = os.path.join(tmp_path, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

@app.blob_trigger(arg_name="myblob", path=AZURE_STORAGE_CONTAINER_NAME_INPUT,
                               connection="documents_storage") 
# def document_image_procesing(myblob: blob.BlobClient):
def document_image_procesing(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {myblob.length} bytes")
    stream = io.BytesIO()
    
    random_foldername = str(uuid.uuid4())
    temp_path = os.getenv('TMPDIR', './tmp')
    temp_path = os.path.join(temp_path, random_foldername)

    create_folder(temp_path)
    create_folder(temp_path, AZURE_STORAGE_CONTAINER_NAME_INPUT)
    create_folder(temp_path, AZURE_STORAGE_CONTAINER_NAME_IMAGES)
    create_folder(temp_path, AZURE_STORAGE_CONTAINER_NAME_DOCS)

    logging.info(f"Temp path: {temp_path}")

    # generate random filename
    random_filename = myblob.name
    temp_path_filename = f"{temp_path}/{random_filename}"
    logging.warn(f"Temp path filename: {temp_path_filename}")

    # save the file to temp path
    with open(temp_path_filename, "wb") as f:
        f.write(myblob.read())

    # out = analyze_layout("myblob.pdf", stream, AZURE_STORAGE_CONTAINER_NAME_IMAGES, AZURE_STORAGE_CONTAINER_NAME_DOCS)
    parsed_content = analyze_layout(temp_path_filename, os.path.join(temp_path, AZURE_STORAGE_CONTAINER_NAME_IMAGES), os.path.join(temp_path, AZURE_STORAGE_CONTAINER_NAME_DOCS))

    # Convert string to bytes
    byte_data = parsed_content.encode('utf-8')

    # Upload data on Blob
    # Get the base name of the file
    _file_name = f"{os.path.basename(myblob.name)}.md"
    logging.info(f"Transcript analysed. Output file: {_file_name} file.")
    blob_client = BlobClient.from_connection_string(conn_str=AZURE_STORAGE_CONNECTION_STRING, container_name=AZURE_STORAGE_CONTAINER_NAME_DOCS, blob_name=_file_name)
    blob_client.upload_blob(byte_data, content_settings=content_settings, overwrite=True)
    blob_client.close()

    # delete the temp folder
    shutil.rmtree(temp_path)

    
    logging.info(f"Processing of {myblob.name} completed.")
    logging.info(f"Output file: {AZURE_STORAGE_CONTAINER_NAME_DOCS}/{_file_name} file.")
    logging.info(f"Output images in container: {AZURE_STORAGE_CONTAINER_NAME_IMAGES} file.")