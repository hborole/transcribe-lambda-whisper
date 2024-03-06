# Create a lambda function to download a file from S3 and transcribe it using OpenAI Whisper small model
# The function will then upload the transcribed file to S3

import traceback
import json
import boto3
import logging
import whisper
import torch
import os

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Set up S3 client
s3 = boto3.client('s3')

def handler(event, context):
    try:
        # Check if NVIDIA GPU is available
        torch.cuda.is_available()
        DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f'Device: {DEVICE}')

        # Model is already present in root
        model = whisper.load_model('./small.pt', device=DEVICE)
        
        logger.info(f'Model loaded successfully')

        # Get the bucket from the lambda environment variables
        bucket = os.environ['BUCKET_NAME']

        # Get the key from the event
        key = json.loads(event['body'])['key']
        
        # Download the file from S3
        local_file = '/tmp/' + key
        s3.download_file(bucket, key, local_file)

        # Log the file download
        logger.info(f'File downloaded from S3: {local_file}')

        audio = whisper.load_audio(local_file)
        audio = whisper.pad_or_trim(audio)

        logger.info(f'Audio loaded successfully')

        # make log-Mel spectrogram and move to the same device as the model
        mel = whisper.log_mel_spectrogram(audio).to(model.device)

        # detect the spoken language
        _, probs = model.detect_language(mel)
        detected_language = max(probs, key=probs.get)
        print(f"Detected language: {detected_language}")

        # decode the audio
        options = whisper.DecodingOptions(fp16=False)
        original = whisper.decode(model, mel, options)
        result = [{'language': detected_language, 'transcript': original.text}]

        # if the language is not English, translate the text
        if detected_language != 'en':
            translate = model.transcribe(local_file, task = "translate", fp16 = False)
            result.append({'language': 'en', 'transcript': translate['text']})
        
        # Log the transcript
        logger.info(f'Transcription: {result}')

        # Upload the json file to S3
        txt_file = '/tmp/' + key + '.txt'
        with open(txt_file, 'w') as f:
            json.dump(result, f)
        s3.upload_file(txt_file, bucket, key + '.txt')
        logger.info(f'Transcription uploaded to S3: {txt_file}')

        # Return a json response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Transcription completed successfully',
                'result': result
            })
        }
    except Exception as e:
        # Log the error and traceback
        logger.error(f"Exception occurred: {str(e)}")
        logger.error(traceback.format_exc())  # This will print the whole traceback
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error occurred in the Lambda function',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
        }