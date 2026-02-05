#!/bin/bash


# Run mongo-express temporarily for debugging

docker run --rm -it \
  --network kreeda-network \
  -e ME_CONFIG_MONGODB_ADMINUSERNAME=admin \
  -e ME_CONFIG_MONGODB_ADMINPASSWORD=password123 \
  -e ME_CONFIG_MONGODB_URL="mongodb://admin:password123@mongodb:27017/" \
  -e ME_CONFIG_BASICAUTH_USERNAME=admin \
  -e ME_CONFIG_BASICAUTH_PASSWORD=admin123 \
  -p 127.0.0.1:8081:8081 \
  mongo-express:1.0.2 &

# Run redis-commander temporarily for debugging

docker run --rm -it \
  --network kreeda-network \
  -e REDIS_HOSTS=local:redis:6379:0:password123 \
  -e HTTP_USER=admin \
  -e HTTP_PASSWORD=admin123 \
  -p 127.0.0.1:8082:8081 \
  rediscommander/redis-commander:latest
