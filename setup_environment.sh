#!/bin/bash

# Setup script for all-dubber environment
# This script sets up the complete environment including TTS models

set -e  # Exit on any error

echo "============================================================"
echo "Linly-Dubbing Environment Setup"
echo "============================================================"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please create and activate a virtual environment first:"
    echo "  python -m venv .venv"
    echo "  source .venv/bin/activate  # Linux/Mac"
    echo "  .venv\\Scripts\\activate     # Windows"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Virtual environment not activated!"
    echo "Please activate the virtual environment:"
    echo "  source .venv/bin/activate  # Linux/Mac"
    echo "  .venv\\Scripts\\activate     # Windows"
    exit 1
fi

echo "✅ Virtual environment detected: $VIRTUAL_ENV"

# Install/upgrade required packages
echo ""
echo "📦 Installing/upgrading required packages..."

# Core packages
pip install --upgrade pip
pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# TTS and audio processing
pip install --upgrade TTS
pip install --upgrade librosa soundfile

# Transformers and ML packages
pip install --upgrade transformers accelerate
pip install --upgrade numpy pandas

# Other dependencies
pip install --upgrade python-dotenv loguru
pip install --upgrade yt-dlp
pip install --upgrade openai

echo "✅ Package installation completed"

# Setup TTS models
echo ""
echo "🎤 Setting up TTS models..."
python setup_tts.py

# Check CUDA availability
echo ""
echo "🔍 Checking CUDA availability..."
python -c "
import torch
if torch.cuda.is_available():
    print(f'✅ CUDA available: {torch.cuda.device_count()} GPU(s)')
    print(f'   Primary GPU: {torch.cuda.get_device_name(0)}')
    memory_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f'   GPU Memory: {memory_gb:.1f} GB')
else:
    print('⚠️  CUDA not available - will use CPU (slower)')
"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Creating .env configuration file..."
    cat > .env << EOF
# Model configuration
MODEL_NAME=Qwen/Qwen3-235B-A22B

# OpenAI API (optional, for OpenAI translation method)
# OPENAI_API_KEY=your_api_key_here
# OPENAI_API_BASE=https://api.openai.com/v1

# Hugging Face token (optional, for private models)
# HF_TOKEN=your_hf_token_here
EOF
    echo "✅ Created .env file with default configuration"
    echo "   Edit .env to add your API keys if needed"
else
    echo "✅ .env file already exists"
fi

# Test basic functionality
echo ""
echo "🧪 Testing basic functionality..."

# Test imports
python -c "
try:
    import torch
    import transformers
    from TTS.api import TTS
    import librosa
    import soundfile
    print('✅ All core imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

echo ""
echo "============================================================"
echo "✅ Environment setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file to add your API keys (if using OpenAI)"
echo "2. Run the dubbing pipeline:"
echo "   python -m tools.do_everything --url 'YOUR_VIDEO_URL'"
echo ""
echo "Example command:"
echo "python -m tools.do_everything \\"
echo "  --url 'https://www.youtube.com/watch?v=VIDEO_ID' \\"
echo "  --translation_method 'LLM' \\"
echo "  --translation_target_language 'Spanish' \\"
echo "  --tts_target_language 'Spanish' \\"
echo "  --voice 'es-ES-ElviraNeural'"
echo "============================================================"
