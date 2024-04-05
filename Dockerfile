FROM public.ecr.aws/lambda/python:3.10

# Copy requirements.txt
COPY requirements.txt .

RUN pip install -r requirements.txt

# Copy your lambda function code into the container
COPY src/* .

RUN yum -y install git wget tar xz
RUN wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && tar xvf ffmpeg-release-amd64-static.tar.xz && mv ffmpeg-6.1-amd64-static/ffmpeg /usr/bin/ffmpeg && rm -Rf ffmpeg*

# Set the CMD to your handler (replace "handler" with your actual handler function name)
CMD ["lambda_function.handler"]