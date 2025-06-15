# -*- coding: utf-8 -*-
import os
from openai import OpenAI
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel
from typing import Optional

# Load environment variables from .env file
load_dotenv()

class TranslationResponse(BaseModel):
    """Structured response for translation requests"""
    translated_text: str
    confidence: Optional[str] = None
    notes: Optional[str] = None

# OpenAI doesn't support repetition_penalty, so we'll use an empty extra_body
extra_body = {}

def openai_response(messages):
    model_name = os.getenv('MODEL_NAME', 'gpt-3.5-turbo')
    client = OpenAI(
        # This is the default and can be omitted
        base_url=os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1'),
        api_key=os.getenv('OPENAI_API_KEY')
    )
    if 'gpt' not in model_name:
        model_name = 'gpt-3.5-turbo'
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        timeout=240,
        extra_body=extra_body
    )
    return response.choices[0].message.content

def openai_structured_translation(messages, target_language="Spanish"):
    """
    Get structured translation response using OpenAI's structured outputs
    """
    model_name = os.getenv('MODEL_NAME', 'gpt-4o-mini')
    client = OpenAI(
        base_url=os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1'),
        api_key=os.getenv('OPENAI_API_KEY')
    )
    
    try:
        response = client.beta.chat.completions.parse(
            model=model_name,
            messages=messages,
            response_format=TranslationResponse,
            timeout=240
        )
        
        # Fix: check for message.parsed instead of choices[0].parsed
        if hasattr(response.choices[0], 'message') and hasattr(response.choices[0].message, 'parsed'):
            parsed_response = response.choices[0].message.parsed
            if parsed_response:
                return parsed_response.translated_text
        
        # Fallback to regular response if parsing fails
        logger.warning("Structured parsing failed, falling back to regular response")
        return openai_response(messages)
            
    except Exception as e:
        logger.warning(f"Structured output failed: {e}, falling back to regular OpenAI")
        return openai_response(messages)

if __name__ == '__main__':
    test_message = [{"role": "user", "content": "你好，介绍一下你自己"}]
    response = openai_structured_translation(test_message)
    print(response)