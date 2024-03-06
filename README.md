# Multimedia Content Translator

This project utilizes the OpenAI Whisper model for speech-to-text conversion, aiming to convert multimedia content to text and subsequently translate it into 99 different languages. The application is packaged as an AWS Lambda function using a Docker container, making it scalable and easy to deploy.

## Features

- **Speech Recognition**: Leverages the powerful OpenAI Whisper model to convert speech in multimedia files into text.
- **Language Translation**: Supports translation of the transcribed text into 99 different languages.
- **AWS Lambda Integration**: Packaged as a Docker image for deployment as an AWS Lambda function, ensuring scalability and manageability.

## Getting Started

These instructions will help you set up and run the project on your local machine for development and testing purposes.

### Prerequisites

Before you begin, ensure you have the following installed:

- Docker
- AWS CLI
- An AWS account with Lambda, IAM, and S3 permissions

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/hborole/transcribe-lambda-whisper.git
   ```

2. Navigate to the project directory

   ```bash
   cd transcribe-lambda-whisper
   ```

3. Build the Docker image:

   ```bash
    docker build -t lambda-whisper .
   ```

4. Run the Docker image:

   ```bash
   docker run --platform linux/amd64 -p 9000:8080 \
    -e BUCKET_NAME=<YOUR_BUCKET_NAME> \
    -v ~/.aws:/root/.aws \
    lambda-whisper:latest
   ```

5. Test the Lambda function:

   ```bash
    curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{ "body": "{ \"key\": \"<FILENAME_FROM_S3_BUCKET.mp4>\" }" }'
   ```

## Usage

The application is designed to be deployed as an AWS Lambda function. The following steps outline the process of deploying the function and testing it.

### Deploying the Lambda Function

1. Create an S3 bucket to store the multimedia files and the translated text.

2. Build the Docker image:

   ```bash
   docker build -t lambda-whisper .
   ```

3. Push the Docker image to Amazon ECR:

   ```bash
    aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account_id>.dkr.ecr.us-east-1.amazonaws.com

    docker tag lambda-whisper:latest <account_id>.dkr.ecr.us-east-1.amazonaws.com/lambda-whisper:latest

    docker push <account_id>.dkr.ecr.us-east-1.amazonaws.com/lambda-whisper:latest
   ```

4. Create the Lambda function:

   ```bash
   aws lambda create-function --function-name multimedia-content-translator \
                           --package-type Image \
                           --code ImageUri=<Your ECR Image URI> \
                           --role <Your Lambda Execution Role ARN> \
                           --timeout 900 \
                           --memory-size 2048
   ```

## Usage

1. Upload a multimedia file to your designated S3 bucket.
2. Invoke the lambda function using the following command:

   ```bash
   aws lambda invoke --function-name multimedia-content-translator --payload '{ "body": "{ \"key\": \"<FILENAME_FROM_S3_BUCKET.mp4>\" }" }' output.json
   ```

3. Check the designated output S3 bucket for the translated text files.

## Configuration

- **BUCKET_NAME**: Environment variable in the Lambda function. Set this to the name of your S3 bucket where the input multimedia files are stored.

## Built With

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech-to-text model.
- [AWS Lambda](https://aws.amazon.com/lambda/) - Event-driven, serverless computing platform.
- [Docker](https://www.docker.com/) - Platform for developing, shipping, and running applications.

## Acknowledgments

- Thanks to OpenAI for providing the Whisper model.
- Thanks to AWS for their Lambda and S3 services.
