# Create a lambda function to download a file from S3 and transcribe it using OpenAI Whisper small model
# The function will then upload the transcribed file to S3

import traceback
import json
import boto3
import logging
import whisper
import os
import json
from transformers import MBartForConditionalGeneration, MBart50TokenizerFast

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Set up S3 client
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Set up the languages

languages = {
    "Arabic": "ar_AR",
    "Czech": "cs_CZ",
    "German": "de_DE",
    "English": "en_XX",
    "Spanish": "es_XX",
    "Estonian": "et_EE",
    "Finnish": "fi_FI",
    "French": "fr_XX",
    "Gujarati": "gu_IN",
    "Hindi": "hi_IN",
    "Italian": "it_IT",
    "Japanese": "ja_XX",
    "Kazakh": "kk_KZ",
    "Korean": "ko_KR",
    "Lithuanian": "lt_LT",
    "Latvian": "lv_LV",
    "Burmese": "my_MM",
    "Nepali": "ne_NP",
    "Dutch": "nl_XX",
    "Romanian": "ro_RO",
    "Russian": "ru_RU",
    "Sinhala": "si_LK",
    "Turkish": "tr_TR",
    "Vietnamese": "vi_VN",
    "Chinese": "zh_CN",
    "Afrikaans": "af_ZA",
    "Azerbaijani": "az_AZ",
    "Bengali": "bn_IN",
    "Persian": "fa_IR",
    "Hebrew": "he_IL",
    "Croatian": "hr_HR",
    "Indonesian": "id_ID",
    "Georgian": "ka_GE",
    "Khmer": "km_KH",
    "Macedonian": "mk_MK",
    "Malayalam": "ml_IN",
    "Mongolian": "mn_MN",
    "Marathi": "mr_IN",
    "Polish": "pl_PL",
    "Pashto": "ps_AF",
    "Portuguese": "pt_XX",
    "Swedish": "sv_SE",
    "Swahili": "sw_KE",
    "Tamil": "ta_IN",
    "Telugu": "te_IN",
    "Thai": "th_TH",
    "Tagalog": "tl_XX",
    "Ukrainian": "uk_UA",
    "Urdu": "ur_PK",
    "Xhosa": "xh_ZA",
    "Galician": "gl_ES",
    "Slovene": "sl_SI",
}

def handler(event, context):
    logger.info(f'Event: {event}')
    try:
        # Get the key from the event
        event_body = json.loads(event['body'])
        key = event_body['key']
        is_translate = event_body.get('is_translate', 'false')
        translate_to = event_body.get('translate_to', 'English')
        transcript = event_body.get('transcript', '')
        
        if is_translate == 'true':
            # Check if the language code is valid
            logger.info(f'Translating to: {translate_to}')
            if translate_to not in languages:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'message': 'Invalid language code',
                        'error': f'{translate_to} is not a valid language code'
                    })
                }

            if transcript == '':
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'message': 'English Transcript not provided',
                        'error': 'English Transcript is required for translation'
                    })
                }

            logger.info(f'Translating text to {translate_to}')

            # Load the model and tokenizer
            model = MBartForConditionalGeneration.from_pretrained("SnypzZz/Llama2-13b-Language-translate")
            tokenizer = MBart50TokenizerFast.from_pretrained("SnypzZz/Llama2-13b-Language-translate", src_lang="en_XX")

            english_text = json.loads(transcript)['english']
            model_inputs = tokenizer(english_text, return_tensors="pt")

            # translate from English to language
            generated_tokens = model.generate(
                **model_inputs,
                forced_bos_token_id=tokenizer.lang_code_to_id[languages[translate_to]]
            )
            translation = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)            
            logger.info(f'Translation to {translate_to}: {translation[0]}')

            result = { 'language': translate_to, 'transcript': translation[0] }
            
        else:
            # Model is already present in root
            model = whisper.load_model('./small.pt', device='cpu')
            # model = whisper.load_model('./base.pt', device='cpu')
            
            logger.info(f'Small model loaded successfully')
            
            # Get the bucket from the lambda environment variables
            bucket = os.environ['BUCKET_NAME']
            
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
            logger.info(f"Detected language: {detected_language}")

            # decode the audio
            options = whisper.DecodingOptions(fp16=False)
            original = whisper.decode(model, mel, options)

            if detected_language != 'en':
                # Translate the audio to English
                translate = model.transcribe(local_file, task="translate", fp16=False)

            result = { 'language': detected_language, 'transcript': original.text, 'english': translate['text'] if detected_language != 'en' else original.text }

            # Log the transcript
            logger.info(f'Transcription: {result}')        

        # Update the dynamodb table with the transcript
        table = dynamodb.Table('lambdaWhisper')

        try:
            if is_translate == 'true':
                # Update a single field in the database
                response = table.update_item(
                    Key={
                        'key': key
                    },
                    UpdateExpression="set statusCode = :s, translated = :tr",
                    ExpressionAttributeValues={
                        ':s': 'COMPLETE',
                        ':tr': result
                    },
                    ReturnValues="ALL_NEW",
                )
                
                logger.info(f"Translation added to dynamodb: {response}")
            else:
                response = table.put_item(
                    Item={
                        'key': key,
                        'statusCode': 'COMPLETE',
                        'transcript': result
                    }
                )
                logger.info(f"Transcript added to dynamodb: {response}")

        except Exception as e:
            logger.error(f"Error adding transcript / translate to dynamodb: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Error occurred in the Lambda function',
                    'error': str(e),
                })
            }

        # Return a json response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Transcription/ translation completed successfully',
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