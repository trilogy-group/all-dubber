#!/bin/bash

# ============================================================================
# IMPORTANT: HuggingFace Model Access Required
# ============================================================================
# Before running this script, you MUST:
# 1. Create a HuggingFace account and get your access token from:
#    https://huggingface.co/settings/tokens
# 2. Accept user conditions for these GATED models (required for diarization):
#    - https://huggingface.co/pyannote/speaker-diarization-3.1
#    - https://huggingface.co/pyannote/segmentation-3.0  
# 3. Add your HF_TOKEN to the .env file:
#    echo "HF_TOKEN=your_token_here" >> .env
# ============================================================================

set -e

echo "Activating virtual environment..."

sudo apt update && sudo apt upgrade -y
sudo apt install nvtop htop
mkdir dubbing
cd dubbing
# clone main repo
git clone https://github.com/Kedreamix/Linly-Dubbing.git --depth 1
# clone submodules
git submodule update --init --recursive

# setup uv
curl -LsSf https://astral.sh/uv/install.sh | sh
uv self update
uv venv --python 3.10 --seed
# install torch and flash attention
uv pip install ninja
#uv pip install torch==2.6.0+cu126 torchvision==0.21.0+cu126 torchaudio==2.6.0+cu126 --index-url https://download.pytorch.org/whl/cu126
#uv pip install https://github.com/Dao-AILab/flash-attention/releases/download/v2.6.3/flash_attn-2.6.3+cu123torch2.3cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
#uv pip install https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.4.post1/flash_attn-2.7.4.post1+cu12torch2.3cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
uv pip install https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.4.post1/flash_attn-2.7.4.post1+cu12torch2.6cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
#uv pip install flash-attn --no-build-isolation
# install system dependencies
sudo apt update
sudo apt install -y ffmpeg python3-dev python3-pip build-essential
# install pynini and other dependencies
uv pip install pynini==2.1.5
uv pip install -r requirements.txt
uv pip install -r requirements_module.txt
uv pip install -r ../requirements_language_packs.txt
uv pip install -e submodules/demucs
uv pip install -e submodules/whisper
uv pip install -e submodules/TTS

# download pretrained models
mkdir -p models/ASR/whisper
wget -nc https://download.pytorch.org/torchaudio/models/wav2vec2_fairseq_base_ls960_asr_ls960.pth \
    -O models/ASR/whisper/wav2vec2_fairseq_base_ls960_asr_ls960.pth
source .venv/bin/activate
python scripts/huggingface_download.py

# launch web UI
cp env.example .env

export CUDNN_PATH="/home/magos/dubbing/all-dubber/.venv/lib/python3.10/site-packages/nvidia/cudnn/lib"
export LD_LIBRARY_PATH="$CUDNN_PATH:$LD_LIBRARY_PATH"

# Setup TTS models (download XTTS and accept license)
echo "Setting up TTS models..."
python setup_tts.py

export video='https://www.youtube.com/watch?v=kUpTUEwKnrk'
#python -m tools.do_everything \
#  --url "https://www.youtube.com/watch?v=67bgwMITsSs" \
#  --translation_target_language "English" \
#  --translation_method "OpenAI" \
#  --tts_target_language "English" \
#  --voice "en-US-JennyNeural" \
#  --voice "es-ES-ElviraNeural" \
#  --asr_method "Whisper" \
#  --num_videos 1

# --url "https://www.youtube.com/watch?v=LB0z43mxTcg" \
# --url "https://www.youtube.com/watch?v=mgOd0S-kN4A" \

python -m tools.do_everything \
  --url "$video" \
  --translation_method "OpenAI" \
  --translation_target_language "Spanish" \
  --tts_target_language "Spanish" \
  --asr_method "WhisperX" \
  --diarization \
  --whisper_min_speakers 2 \
  --whisper_max_speakers 4 \
  --num_videos 1