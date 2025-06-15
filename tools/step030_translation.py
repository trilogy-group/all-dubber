# -*- coding: utf-8 -*-
import json
import os
import re

from dotenv import load_dotenv
import time
from loguru import logger
from tools.step031_translation_openai import openai_response, openai_structured_translation
from tools.step032_translation_llm import llm_response
from tools.step033_translation_translator import translator_response
from tools.step034_translation_ernie import ernie_response
from tools.step035_translation_qwen import qwen_response
from tools.step036_translation_ollama import ollama_response

load_dotenv()
import traceback

def get_necessary_info(info: dict):
    return {
        'title': info['title'],
        'uploader': info['uploader'],
        'description': info['description'],
        'upload_date': info['upload_date'],
        # 'categories': info['categories'],
        'tags': info['tags'],
    }

def ensure_transcript_length(transcript, max_length=4000):
    mid = len(transcript)//2
    before, after = transcript[:mid], transcript[mid:]
    length = max_length//2
    return before[:length] + after[-length:]

def split_text_into_sentences(para):
    para = re.sub('([。！？\?])([^，。！？\?”’》])', r"\1\n\2", para)  # 单字符断句符
    para = re.sub('(\.{6})([^，。！？\?”’》])', r"\1\n\2", para)  # 英文省略号
    para = re.sub('(\…{2})([^，。！？\?”’》])', r"\1\n\2", para)  # 中文省略号
    para = re.sub('([。！？\?][”’])([^，。！？\?”’》])', r'\1\n\2', para)
    # 如果双引号前有终止符，那么双引号才是句子的终点，把分句符\n放到双引号后，注意前面的几句都小心保留了双引号
    para = para.rstrip()  # 段尾如果有多余的\n就去掉它
    # 很多规则中会考虑分号;，但是这里我把它忽略不计，破折号、英文双引号等同样忽略，需要的再做些简单调整即可。
    return para.split("\n")

def translation_postprocess(result, target_language='简体中文'):
    # Remove parenthetical content
    result = re.sub(r'\（[^)]*\）', '', result)
    result = result.replace('...', '，')
    
    # Apply Chinese-specific postprocessing only for Chinese
    if target_language == '简体中文':
        result = re.sub(r'(?<=\d),(?=\d)', '', result)
        result = result.replace('²', '的平方').replace(
            '————', '：').replace('——', '：').replace('°', '度')
        result = result.replace("AI", '人工智能')
        result = result.replace('变压器', "Transformer")
    else:
        # For other languages, keep numbers and symbols as-is
        # Only do basic cleanup
        result = result.replace('————', ':').replace('——', ':')
    
    return result

def valid_translation(text, translation, target_language='简体中文'):
    
    if (translation.startswith('```') and translation.endswith('```')):
        translation = translation[3:-3]
        return True, translation_postprocess(translation, target_language)
    
    if (translation.startswith('"') and translation.endswith('"')) or (translation.startswith('"') and translation.endswith('"')):
        translation = translation[1:-1]
        return True, translation_postprocess(translation, target_language)
    
    # Handle Chinese format responses
    if ('翻译' in translation or "译文" in translation) and '："' in translation and '"' in translation:
        translation = translation.split('："')[-1].split('"')[0]
        return True, translation_postprocess(translation, target_language)
    
    if ('翻译' in translation or "译文" in translation) and '："' in translation and '"' in translation:
        translation = translation.split('："')[-1].split('"')[0]
        return True, translation_postprocess(translation, target_language)

    if ('翻译' in translation or "译文" in translation) and ':"' in translation and '"' in translation:
        translation = translation.split(':"')[-1].split('"')[0]
        return True, translation_postprocess(translation, target_language)
    
    if ('翻译' in translation or "译文" in translation) and ': "' in translation and '"' in translation:
        translation = translation.split(': "')[-1].split('"')[0]
        return True, translation_postprocess(translation, target_language)
    
    # Handle English/Spanish format responses
    if 'Translated text:' in translation and '"' in translation:
        # Extract content between quotes after "Translated text:"
        parts = translation.split('Translated text:')[-1]
        if '"' in parts:
            translation = parts.split('"')[1] if parts.count('"') >= 2 else parts.split('"')[0]
            return True, translation_postprocess(translation, target_language)
    
    # Handle Spanish format responses
    if ('traducción:' in translation.lower() or 'translation:' in translation.lower()) and '"' in translation:
        # Extract content between quotes after "traducción:" or "translation:"
        parts = translation.lower()
        if 'traducción:' in parts:
            parts = translation.split('traducción:')[-1]
        elif 'translation:' in parts:
            parts = translation.split('translation:')[-1]
        
        if '"' in parts:
            translation = parts.split('"')[1] if parts.count('"') >= 2 else parts.split('"')[0]
            return True, translation_postprocess(translation, target_language)

    # Much more lenient length validation - especially for technical content
    if len(text) <= 15:  # Increased threshold for short text
        # Very generous limit for short technical phrases with numbers
        if len(translation) > 100:  # Much more generous
            return False, f'Translation too long for short text.'
    elif len(translation) > len(text) * 3:  # Much more generous ratio
        return False, f'Translation significantly too long.'
    
    # Minimal forbidden words - only block obvious errors
    forbidden = ['\n']  # Only block newlines
    
    translation = translation.strip()
    for word in forbidden:
        if word in translation:
            return False, f"Invalid character in translation."
    
    return True, translation_postprocess(translation, target_language)

def split_sentences(translation, use_char_based_end=True):
    output_data = []
    for item in translation:
        start = item['start']
        text = item['text']
        speaker = item['speaker']
        translation_text = item['translation']

        # 检查翻译文本是否为空
        if not translation_text or len(translation_text.strip()) == 0:
            # 如果翻译为空，直接使用原始时间范围并跳过分割
            output_data.append({
                "start": round(start, 3),
                "end": round(item['end'], 3),
                "text": text,
                "speaker": speaker,
                "translation": translation_text or "未翻译"  # 如果是空字符串，提供默认值
            })
            continue

        sentences = split_text_into_sentences(translation_text)

        if use_char_based_end:
            # 避免除以零错误
            duration_per_char = (item['end'] - item['start']) / max(1, len(translation_text))
        else:
            duration_per_char = 0

        # logger.info(f'Char duration: {duration_per_char}')
        for sentence in sentences:
            if use_char_based_end:
                sentence_end = start + duration_per_char * len(sentence)
            else:
                sentence_end = item['end']

            # Append the new item
            output_data.append({
                "start": round(start, 3),
                "end": round(sentence_end, 3),
                "text": text,
                "speaker": speaker,
                "translation": sentence
            })

            # Update the start for the next sentence
            if use_char_based_end:
                start = sentence_end

    return output_data

def summarize(info, transcript, target_language='简体中文', method = 'LLM'):
    transcript = ' '.join(line['text'] for line in transcript)
    transcript = ensure_transcript_length(transcript, max_length=2000)
    info_message = f'Title: "{info["title"]}" Author: "{info["uploader"]}". ' 
    
    if method in ['Google Translate', 'Bing Translate']:
        full_description = f'{info_message}\n{transcript}\n{info_message}\n'
        translation = translator_response(full_description, target_language)
        return {
                'title': translator_response(info['title'], target_language),
                'author': info['uploader'],
                'summary': translation,
                'language': target_language
            }

    full_description = f'The following is the full content of the video:\n{info_message}\n{transcript}\n{info_message}\nAccording to the above content, summarize the video CONCISELY in JSON format:\n```json\n{{"title": "", "summary": ""}}\n```'
    
    model_name = os.getenv('MODEL_NAME', '')
    is_qwen3 = 'Qwen3' in model_name or 'qwen3' in model_name.lower()
    nothink_prefix = '/nothink ' if is_qwen3 else ''
    nothink_suffix = ' Do not include any reasoning or thinking process in your response.' if is_qwen3 else ''
    
    messages = [
        {'role': 'system',
            'content': f'{nothink_prefix}You are a expert in the field of this video. Please summarize the video CONCISELY in JSON format. Keep the summary under 200 words.\n```json\n{{"title": "the title of the video", "summary": "the summary of the video"}}\n```{nothink_suffix}'},
        {'role': 'user', 'content': full_description},
    ]
    retry_message=''
    success = False
    for retry in range(9):
        try:
            messages = [
                {'role': 'system', 'content': f'{nothink_prefix}You are a expert in the field of this video. Please summarize the video CONCISELY in JSON format. Keep the summary under 200 words.\n```json\n{{"title": "the title of the video", "summary": "the summary of the video"}}\n```{nothink_suffix}'},
                {'role': 'user', 'content': full_description+retry_message},
            ]
            if method == 'LLM':
                response = llm_response(messages)
            elif method == 'OpenAI':
                response = openai_response(messages)
            elif method == 'Ernie':
                system_content = messages[0]['content']
                user_messages = messages[1:]
                response = ernie_response(user_messages, system=system_content)
            elif method == '阿里云-通义千问':
                response = qwen_response(messages)
            elif method == 'Ollama':  # 添加对Ollama的支持
                response = ollama_response(messages)
            else:
                raise Exception('Invalid method')
            summary = response.replace('\n', '')
            if '视频标题' in summary:
                raise Exception("包含“视频标题”")
            logger.info(summary)
            
            # Better JSON extraction that handles nested objects and truncated responses
            try:
                # Remove newlines but preserve structure
                clean_response = summary.strip()
                
                # First try to find complete JSON block
                json_match = re.search(r'\{.*\}', clean_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # Try to extract from ```json blocks (may be incomplete)
                    json_match = re.search(r'```json\s*(\{.*)', clean_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        # If JSON is incomplete, try to fix it
                        if not json_str.rstrip().endswith('}'):
                            # Try to find title and summary parts
                            title_match = re.search(r'"title":\s*"([^"]*)"', json_str)
                            summary_match = re.search(r'"summary":\s*"([^"]*)', json_str)
                            
                            if title_match and summary_match:
                                title = title_match.group(1)
                                summary_text = summary_match.group(1)
                                # Reconstruct complete JSON
                                json_str = f'{{"title": "{title}", "summary": "{summary_text}"}}'
                            else:
                                raise Exception("Incomplete JSON and cannot reconstruct")
                    else:
                        # Last resort: look for any JSON-like structure
                        json_match = re.search(r'\{[^}]*"title"[^}]*\}', clean_response)
                        if json_match:
                            json_str = json_match.group(0)
                        else:
                            raise Exception("No JSON found in response")
                
                summary = json.loads(json_str)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"JSON parsing failed: {e}")
                logger.warning(f"Raw response: {response}")
                raise Exception(f"Failed to parse JSON: {e}")
                
            summary = {
                'title': summary.get('title', '').replace('title:', '').strip(),
                'summary': summary.get('summary', '').replace('summary:', '').strip()
            }
            if summary['title'] == '' or summary['summary'] == '':
                raise Exception('Invalid summary')
            
            if 'title' in summary['title']:
                raise Exception('Invalid summary')
            success = True
            break
        except Exception as e:
            traceback.print_exc()
            retry_message += '\nSummarize the video in JSON format:\n```json\n{"title": "", "summary": ""}\n```'
            logger.warning(f'总结失败\n{e}')
            time.sleep(1)
            
    if not success:
        raise Exception(f'总结失败')
            
    messages = [
        {'role': 'system',
            'content': f'You are a native speaker of {target_language}. Please translate the title and summary into {target_language} in JSON format. ```json\n{{"title": "the {target_language} title of the video", "summary", "the {target_language} summary of the video", "tags": [list of tags in {target_language}]}}\n```.'},
        {'role': 'user',
            'content': f'The title of the video is "{summary["title"]}". The summary of the video is "{summary["summary"]}". Tags: {info["tags"]}.\nPlease translate the above title and summary and tags into {target_language} in JSON format. ```json\n{{"title": "", "summary", ""， "tags": []}}\n```. Remember to tranlate the title and the summary and tags into {target_language} in JSON.'},
    ]
    while True:
        try: 
            logger.info(summary)
            if target_language in summary['title'] or target_language in summary['summary']:
                raise Exception('Invalid translation')
            title = summary['title'].strip()
            if (title.startswith('"') and title.endswith('"')) or (title.startswith('“') and title.endswith('”')) or (title.startswith('‘') and title.endswith('’')) or (title.startswith("'") and title.endswith("'")) or (title.startswith('《') and title.endswith('》')):
                title = title[1:-1]
            result = {
                'title': title,
                'author': info['uploader'],
                'summary': summary['summary'],
                'tags': info['tags'],
                'language': target_language
            }
            return result
        except Exception as e:
            logger.warning(f'总结翻译失败\n{e}')
            time.sleep(1)

def _translate(summary, transcript, target_language='简体中文', method='LLM'):

    info = f'This is a video called "{summary["title"]}". {summary["summary"]}.'
    full_translation = []
    
    # Check if we're using Qwen3 model to add /nothink instruction
    model_name = os.getenv('MODEL_NAME', '')
    is_qwen3 = 'Qwen3' in model_name or 'qwen3' in model_name.lower()
    nothink_prefix = '/nothink ' if is_qwen3 else ''
    nothink_suffix = ' Do not include any reasoning or thinking process in your response.' if is_qwen3 else ''
    
    if target_language == '简体中文':
        fixed_message = [
            {'role': 'system', 'content': f'{nothink_prefix}You are an expert in the field of this video.\n{info}\nTranslate the sentence into {target_language}. 下面我让你来充当翻译家，你的目标是把任何语言翻译成{target_language}，请翻译时不要带翻译腔，而是要翻译得自然、流畅和地道，使用优美和高雅的表达方式。请将人工智能的"agent"翻译为"智能体"，强化学习中是`Q-Learning`而不是`Queue Learning`。数学公式写成plain text，不要使用latex。确保翻译正确和简洁。注意信达雅。{nothink_suffix}'},
            {'role': 'user', 'content': f'使用地道的{target_language}Translate:"Knowledge is power."'},
            {'role': 'assistant', 'content': '翻译："知识就是力量。"'},
            {'role': 'user', 'content': f'使用地道的{target_language}Translate:"To be or not to be, that is the question."'},
            {'role': 'assistant', 'content': '翻译："生存还是毁灭，这是一个值得考虑的问题。"'},
        ]
    else:
        # For other languages, we keep the template general
        fixed_message = [
            {'role': 'system', 'content': f'{nothink_prefix}You are a professional translator specializing in technical video content translation. Your task is to translate the transcript of a video titled "{summary["title"]}". The video summary is: {summary["summary"]}. Translate each sentence accurately into {target_language}, maintaining the original meaning, tone, and context. IMPORTANT RULES: 1) Keep technical terms like "AI", "API", "GPU", "CPU" as-is unless there is a well-established translation. 2) Keep numbers as numbers (e.g., "2024" stays "2024", "32B" stays "32B"). 3) Keep model names and technical specifications unchanged. 4) Return only the translated text without any prefixes, explanations, or formatting.{nothink_suffix}'},
            {'role': 'user', 'content': 'Translate: "Knowledge is power."'},
            {'role': 'assistant', 'content': 'El conocimiento es poder.'},
            {'role': 'user', 'content': 'Translate: "The AI model has 32B parameters and was released in 2024."'},
            {'role': 'assistant', 'content': 'El modelo de AI tiene 32B parámetros y fue lanzado en 2024.'},
        ]
        
    history = []
    
    for line in transcript:
        text = line['text']

        retry_message = 'Only translate the quoted sentence and give me the final translation.'
        if method == 'Google Translate':
            translation = translator_response(text, to_language = target_language, translator_server='google')
        elif method == 'Bing Translate':
            translation = translator_response(text, to_language = target_language, translator_server='bing')
        else:
            for retry in range(10):
                messages = fixed_message + \
                    history[-30:] + [{'role': 'user',
                                    'content': f'Translate:"{text}"'}]
                # print(messages)
                try:
                    if method == 'LLM':
                        response = llm_response(messages)
                    elif method == 'OpenAI':
                        response = openai_structured_translation(messages, target_language)
                        # Structured outputs return clean text, minimal validation needed
                        translation = response.strip()
                        logger.info(f'原文：{text}')
                        logger.info(f'译文：{translation}')
                        # Skip complex validation for structured outputs
                        break
                    elif method == 'Ernie':
                        system_content = messages[0]['content']
                        user_messages = messages[1:]
                        response = ernie_response(user_messages, system=system_content)
                    elif method == '阿里云-通义千问':
                        response = qwen_response(messages)
                    elif method == 'Ollama':  # 添加对Ollama的支持
                        response = ollama_response(messages)
                    else:
                        raise Exception('Invalid method')
                    
                    # Only apply complex validation for non-structured methods
                    if method == 'OpenAI':
                        # OpenAI structured outputs are already clean, skip validation
                        translation = response.strip()
                        logger.info(f'原文：{text}')
                        logger.info(f'译文：{translation}')
                        break
                    elif method == 'LLM':
                        # LLM responses are now cleaned, apply minimal validation
                        translation = response.replace('\n', '')
                        logger.info(f'原文：{text}')
                        logger.info(f'译文：{translation}')
                        # Skip complex validation for cleaned LLM responses
                        break
                    else:
                        # Apply validation for other methods (Google Translate, Bing, etc.)
                        translation = response.replace('\n', '')
                        logger.info(f'原文：{text}')
                        logger.info(f'译文：{translation}')
                        success, translation = valid_translation(text, translation, target_language)
                        if not success:
                            # Simple retry message without accumulating errors
                            logger.warning(f'Validation failed for: {text} -> {translation}. Retrying...')
                            continue
                    break
                except Exception as e:
                    logger.error(e)
                    logger.warning('翻译失败')
                    time.sleep(1)
        full_translation.append(translation)
        
        # Build history with consistent format based on target language
        if target_language == '简体中文':
            history.append({'role': 'user', 'content': f'Translate:"{text}"'})
            history.append({'role': 'assistant', 'content': f'翻译："{translation}"'})
        else:
            history.append({'role': 'user', 'content': f'Translate the following text: "{text}"'})
            history.append({'role': 'assistant', 'content': f'Translated text: "{translation}"'})
        
        time.sleep(0.1)
        
    return full_translation

def translate(method, folder, target_language='简体中文'):
    if os.path.exists(os.path.join(folder, 'translation.json')):
        logger.info(f'Translation already exists in {folder}')
        return True
    
    info_path = os.path.join(folder, 'download.info.json')
    # 不一定要download.info.json
    if os.path.exists(info_path):
        with open(info_path, 'r', encoding='utf-8') as f:
            info = json.load(f)
        info = get_necessary_info(info)
    else:
        info = {
            'title': os.path.basename(folder),
            'uploader': 'Unknown',
            'description': 'Unknown',
            'upload_date': 'Unknown',
            'tags': []
        }
    transcript_path = os.path.join(folder, 'transcript.json')
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript = json.load(f)
    
    summary_path = os.path.join(folder, 'summary.json')
    if os.path.exists(summary_path):
        summary = json.load(open(summary_path, 'r', encoding='utf-8'))
    else:
        summary = summarize(info, transcript, target_language, method)
        if summary is None:
            logger.error(f'Failed to summarize {folder}')
            return False
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    translation_path = os.path.join(folder, 'translation.json')
    translation = _translate(summary, transcript, target_language, method)
    for i, line in enumerate(transcript):
        line['translation'] = translation[i]
    transcript = split_sentences(transcript)
    with open(translation_path, 'w', encoding='utf-8') as f:
        json.dump(transcript, f, indent=2, ensure_ascii=False)
    return summary, transcript

def translate_all_transcript_under_folder(folder, method, target_language):
    summary_json , translate_json = None, None
    for root, dirs, files in os.walk(folder):
        if 'transcript.json' in files and 'translation.json' not in files:
            summary_json , translate_json = translate(method, root, target_language)
        elif 'translation.json' in files:
            summary_json = json.load(open(os.path.join(root, 'summary.json'), 'r', encoding='utf-8'))
            translate_json = json.load(open(os.path.join(root, 'translation.json'), 'r', encoding='utf-8'))
    print(summary_json, translate_json)
    return f'Translated all videos under {folder}',summary_json , translate_json

if __name__ == '__main__':
    # translate_all_transcript_under_folder(r'videos', 'LLM' , '简体中文')
    # translate_all_transcript_under_folder(r'videos', 'OpenAI' , '简体中文')
    translate_all_transcript_under_folder(r'videos', 'ernie' , '简体中文')