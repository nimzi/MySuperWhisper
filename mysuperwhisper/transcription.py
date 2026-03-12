"""
Whisper transcription engine for MySuperWhisper.
Handles model loading and speech-to-text conversion.
"""

import gc
from faster_whisper import WhisperModel
from .config import log, config

# Global model instance
_model = None
_is_cpu_mode = False


def load_model(model_size=None):
    """
    Load the Whisper model.

    Attempts to use GPU (CUDA) first, falls back to CPU if unavailable.
    Uses INT8 quantization for lower memory usage.

    Args:
        model_size: Model size ('tiny', 'base', 'small', 'medium', 'large-v3')
                   If None, uses config.model_size

    Returns:
        bool: True if GPU mode, False if CPU mode
    """
    global _model, _is_cpu_mode

    size = model_size or config.model_size
    log(f"Loading Faster-Whisper model '{size}'...")

    try:
        _model = WhisperModel(size, device="cuda", compute_type="int8")
        _is_cpu_mode = False
        log("Model loaded successfully on GPU (INT8).")
        return True
    except Exception as e:
        log(f"GPU error: {e}", "warning")
        log("Falling back to CPU (INT8)...", "warning")
        _model = WhisperModel(size, device="cpu", compute_type="int8")
        _is_cpu_mode = True
        log("Model loaded on CPU (degraded mode).", "warning")
        return False


def reload_model(new_model_size):
    """
    Reload the model with a different size.

    Args:
        new_model_size: New model size to load

    Returns:
        bool: True if successful
    """
    global _model, _is_cpu_mode

    log(f"Model change requested: {config.model_size} -> {new_model_size}...")

    try:
        # Delete old model first to free memory
        if _model:
            del _model
            gc.collect()

        # Try GPU first
        try:
            new_model = WhisperModel(new_model_size, device="cuda", compute_type="int8")
            _is_cpu_mode = False
            log(f"New model '{new_model_size}' loaded on GPU.")
        except Exception as gpu_err:
            log(f"GPU error: {gpu_err}", "warning")
            log("Falling back to CPU (INT8)...", "warning")
            new_model = WhisperModel(new_model_size, device="cpu", compute_type="int8")
            _is_cpu_mode = True
            log(f"New model '{new_model_size}' loaded on CPU (degraded mode).", "warning")

        _model = new_model
        config.model_size = new_model_size
        return True

    except Exception as e:
        log(f"Error loading model {new_model_size}: {e}", "error")
        log("Attempting to reload previous model 'medium'...", "warning")

        try:
            _model = WhisperModel("medium", device="cuda", compute_type="int8")
            config.model_size = "medium"
            _is_cpu_mode = False
        except:
            try:
                _model = WhisperModel("medium", device="cpu", compute_type="int8")
                config.model_size = "medium"
                _is_cpu_mode = True
            except:
                pass

        return False


def transcribe(audio_data, language=None, task="transcribe"):
    """
    Transcribe audio to text.

    Args:
        audio_data: Audio data at 16kHz (use audio.prepare_for_whisper first)
        language: Language code ('en', 'fr', 'es', etc.) or None for auto-detect
        task: "transcribe" or "translate" (translate converts to English)

    Returns:
        str: Transcribed text, or empty string if nothing detected
    """
    if _model is None:
        log("Model not loaded!", "error")
        return ""

    try:
        # Faster-Whisper returns a generator of segments
        segments, info = _model.transcribe(audio_data, beam_size=5, language=language, task=task)

        # Reconstruct full text
        full_text = []
        for segment in segments:
            full_text.append(segment.text)

        return " ".join(full_text).strip()

    except Exception as e:
        log(f"Transcription error: {e}", "error")
        raise


def is_cpu_mode():
    """Check if model is running in CPU mode (degraded)."""
    return _is_cpu_mode


def is_model_loaded():
    """Check if model is loaded."""
    return _model is not None
