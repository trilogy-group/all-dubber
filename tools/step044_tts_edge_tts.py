import os
from loguru import logger
import numpy as np
import torch
import time
from .utils import save_wav
import sys
import subprocess
import shlex

import torchaudio
model = None



#  <|zh|><|en|><|jp|><|yue|><|ko|> for Chinese/English/Japanese/Cantonese/Korean
language_map = {
    '中文': 'zh-CN-XiaoxiaoNeural',
    'English': 'en-US-MichelleNeural',
    'Japanese': 'ja-JP-NanamiNeural',
    '粤语': 'zh-HK-HiuMaanNeural',
    'Korean': 'ko-KR-SunHiNeural'
}

def tts(text, output_path, target_language='中文', voice = 'zh-CN-XiaoxiaoNeural'):
    if os.path.exists(output_path):
        logger.info(f'TTS {text} 已存在')
        return
    for retry in range(3):
        try:
            # Use subprocess with proper argument handling instead of os.system
            mp3_path = output_path.replace(".wav", ".mp3")
            cmd = [
                'edge-tts',
                '--text', text,
                '--write-media', mp3_path,
                '--voice', voice
            ]
            
            # Run the command safely
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f'TTS {text}')
            break
        except subprocess.CalledProcessError as e:
            logger.warning(f'TTS {text} 失败')
            logger.warning(f'Command failed with return code {e.returncode}')
            logger.warning(f'stderr: {e.stderr}')
            if retry == 2:  # Last retry
                logger.error(f'EdgeTTS failed after 3 retries for text: {text}')
        except Exception as e:
            logger.warning(f'TTS {text} 失败')
            logger.warning(e)


if __name__ == '__main__':
    speaker_wav = r'videos/村长台钓加拿大/20240805 英文无字幕 阿里这小子在水城威尼斯发来问候/audio_vocals.wav'
    while True:
        text = input('请输入：')
        tts(text, f'playground/{text}.wav', target_language='中文')
