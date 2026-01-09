FROM python:3.14-slim

# Install Lambda Web Adapter (allows running standard HTTP apps or straight functions)
# For standard Lambda handlers in Docker using Python base images, 
# we usually use the AWS Lambda Python Runtime Interface Client (RIC).
# However, 3.14 is very new. We will install RIC if available or use a custom entrypoint.

# Set working directory
WORKDIR /var/task

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install awslambdaric to implement the Lambda Runtime API
RUN pip install awslambdaric

# Set ENTRYPOINT to invoke the RIC
ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]

# Set the CMD to your handler (could be overridden per function)
CMD [ "collector.handler" ]
