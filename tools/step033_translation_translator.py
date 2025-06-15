# -*- coding: utf-8 -*-
import json
import os
import translators as ts
from dotenv import load_dotenv
from loguru import logger
load_dotenv()

def translator_response(messages, to_language = 'zh-CN', translator_server = 'bing'):
    if '中文' in to_language:
        to_language = 'zh-CN'
    elif 'English' in to_language:
        to_language = 'en'
    elif 'Spanish' in to_language or 'Español' in to_language or 'español' in to_language:
        to_language = 'es'
    elif 'French' in to_language or 'Français' in to_language or 'français' in to_language:
        to_language = 'fr'
    elif 'German' in to_language or 'Deutsch' in to_language or 'deutsch' in to_language:
        to_language = 'de'
    elif 'Italian' in to_language or 'Italiano' in to_language or 'italiano' in to_language:
        to_language = 'it'
    elif 'Portuguese' in to_language or 'Português' in to_language or 'português' in to_language:
        to_language = 'pt'
    elif 'Japanese' in to_language or '日本語' in to_language:
        to_language = 'ja'
    elif 'Korean' in to_language or '한국어' in to_language:
        to_language = 'ko'
    translation = ''
    for retry in range(3):
        try:
            translation = ts.translate_text(query_text=messages, translator=translator_server, from_language='auto', to_language=to_language)
            break
        except Exception as e:
            logger.info(f'translate failed! {e}')
            print('tranlate failed!')
    return translation

if __name__ == '__main__':
    response = translator_response('Hello, how are you?', '中文', 'bing')
    print(response)
    response = translator_response('你好，最近怎么样？ ', 'en', 'google')
    print(response)