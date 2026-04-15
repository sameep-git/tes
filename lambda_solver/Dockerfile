# Lambda container image for the TES OR-Tools solver.
# Built on the AWS Lambda Python 3.11 base image (x86_64).
#
# Build & push to ECR:
#   aws ecr create-repository --repository-name tes-solver --region us-east-1
#   docker build -t tes-solver .
#   docker tag tes-solver:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/tes-solver:latest
#   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
#   docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/tes-solver:latest

FROM public.ecr.aws/lambda/python:3.11

# Install Python dependencies (OR-Tools ships pre-built manylinux wheels — no compiler needed)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy solver code
COPY handler.py solver_core.py ./

# Lambda expects this CMD format
CMD ["handler.lambda_handler"]
