import os
import subprocess
import tempfile
import logging
import soundfile as sf
from kokoro import KPipeline

logger = logging.getLogger(__name__)

def text_to_speech(text, output_mp3):
    """
    Converts the provided text to speech using KPipeline.
    Generates a temporary WAV file and converts it to MP3 using ffmpeg.
    """
    logger.info("Starting text-to-speech conversion.")
    pipeline = KPipeline(lang_code="a")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        temp_wav_path = tmp_wav.name
    logger.debug("Temporary WAV file created at %s", temp_wav_path)

    try:
        generator = pipeline(text, voice="af_bella", speed=1, split_pattern=r"\n+")
        with sf.SoundFile(temp_wav_path, "w", 24000, channels=1) as f:
            for chunk_index, (_, _, audio) in enumerate(generator):
                logger.debug("Writing audio chunk %d to WAV file.", chunk_index)
                f.write(audio)
        logger.info("WAV file generated. Converting to MP3 with ffmpeg.")
        subprocess.run(["ffmpeg", "-y", "-i", temp_wav_path, output_mp3], check=True)
        logger.info("MP3 file created at %s", output_mp3)
    finally:
        if os.path.exists(temp_wav_path):
            os.unlink(temp_wav_path)
            logger.debug("Temporary WAV file %s removed.", temp_wav_path)