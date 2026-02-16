FROM python:3.9

WORKDIR /code

# Copy requirements and install dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Install Playwright and its dependencies (Chromium)
RUN playwright install --with-deps chromium

# Copy the rest of the application
COPY . /code

# Create directory for data persistence (HuggingFace Spaces uses /data usually if mounted, 
# but here we use the app directory or specific path. 
# HF Spaces persistence usually requires a dataset mount or similar, 
# but for basic file storage we just ensuring the folder exists)
RUN mkdir -p /code/data && chmod 777 /code/data

# Expose the port (HuggingFace expects 7860)
EXPOSE 7860

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
