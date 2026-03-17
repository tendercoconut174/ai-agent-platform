"""Audio output formatter – TTS via OpenAI."""

import base64
import logging
import os
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


def text_to_audio_base64(text: str) -> Optional[dict[str, str]]:
    """Convert text to speech and return base64-encoded audio.

    Returns:
        Dict with content_base64, content_type, filename, or None on failure.
    """
    logger.info("[audio] text_to_audio_base64 | text_len=%d", len(text))
    from shared.mcp.tools.media_processor import text_to_speech

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        result = text_to_speech(text=text[:4096], output_path=tmp_path)
        if result.get("error"):
            return None
        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
        return {
            "content_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "content_type": "audio/mpeg",
            "filename": "result.mp3",
        }
    except Exception as e:
        logger.warning("[audio] text_to_audio_base64 failed: %s", e)
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
