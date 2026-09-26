#!/bin/bash

source /etc/docker/.env 
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$GOOGLE_API_KEY" | grep -i "live\|native-audio"
