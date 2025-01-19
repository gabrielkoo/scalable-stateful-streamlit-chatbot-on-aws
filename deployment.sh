#!/bin/bash
DOCKER_REPO_NAME=streamlit-chatbot
DOCKER_TAG=latest

if [ -z "$AWS_REGION" ]; then
  echo "AWS_REGION is not set"
  exit 1
fi


AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$AWS_ACCOUNT" ]; then
  echo "Please authenticate with aws-cli before running this script"
  exit 1
fi

docker build \
  --platform=linux/arm64 \
  -t $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$DOCKER_REPO_NAME:$DOCKER_TAG .
if [ $? -ne 0 ]; then
  echo "Docker build failed"
  exit 1
fi

aws ecr get-login-password \
    --region $AWS_REGION \
    | docker login \
        --username AWS \
        --password-stdin $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$DOCKER_REPO_NAME:$DOCKER_TAG
echo "Docker image pushed"

aws ecs update-service \
    --cluster streamlit-chatbot-cluster \
    --service streamlit-chatbot-service \
    --force-new-deployment \
    --desired-count 1 \
    --region $AWS_REGION | jq -r '.service.deployments[0].rolloutState'
