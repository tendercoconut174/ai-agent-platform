"""Media processing tool – audio transcription (Whisper), TTS, image description."""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def transcribe_audio(file_path: str) -> dict[str, Any]:
    """Transcribe an audio file using OpenAI Whisper API.

    Args:
        file_path: Path to the audio file.

    Returns:
        Dict with text, language, and duration.
    """
    logger.info("[media_processor] transcribe_audio | file=%s", file_path)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("[media_processor] OPENAI_API_KEY not set")
        return {"text": "", "error": "OPENAI_API_KEY not set"}

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    with open(file_path, "rb") as f:
        result = client.audio.transcriptions.create(model="whisper-1", file=f)
    logger.info("[media_processor] transcribe_audio DONE | text_len=%d", len(result.text))
    return {"text": result.text, "error": None}


def text_to_speech(text: str, output_path: str, voice: str = "alloy") -> dict[str, Any]:
    """Convert text to speech using OpenAI TTS API.

    Args:
        text: Text to convert.
        output_path: Path to save the audio file.
        voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer).

    Returns:
        Dict with output_path, size, and error.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"output_path": output_path, "error": "OPENAI_API_KEY not set"}

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.audio.speech.create(model="tts-1", voice=voice, input=text)
    response.stream_to_file(output_path)
    file_size = os.path.getsize(output_path)
    return {"output_path": output_path, "size": file_size, "error": None}


def describe_image(file_path: str) -> dict[str, Any]:
    """Describe an image using GPT-4 Vision.

    Args:
        file_path: Path to the image file.

    Returns:
        Dict with description and error.
    """
    logger.info("[media_processor] describe_image | file=%s", file_path)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("[media_processor] OPENAI_API_KEY not set")
        return {"description": "", "error": "OPENAI_API_KEY not set"}

    import base64

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    ext = file_path.rsplit(".", 1)[-1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/png")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image in detail."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
        max_tokens=1000,
    )
    desc = response.choices[0].message.content
    logger.info("[media_processor] describe_image DONE | desc_len=%d", len(desc or ""))
    return {"description": desc, "error": None}
