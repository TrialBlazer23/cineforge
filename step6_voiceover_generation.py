import argparse
import os
from typing import List
from google.cloud import texttospeech


def extract_dialogue(screenplay: str) -> str:
    """Extract dialogue lines from a screenplay.

    This simple extractor ignores scene headings, character names (assumed uppercase),
    and parenthetical directions starting with '('.
    """
    lines: List[str] = []
    for raw_line in screenplay.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Skip scene headings and character names
        if line.isupper() or line.startswith(("SCENE", "INT.", "EXT.")):
            continue
        # Skip parentheticals
        if line.startswith("("):
            continue
        # Keep dialogue or action lines
        lines.append(line)
    return " ".join(lines)


def generate_voiceover(project_id: str, screenplay_path: str, output_path: str) -> None:
    """Generate a voiceover audio file from a screenplay using Google Cloud Text-to-Speech."""
    client = texttospeech.TextToSpeechClient()
    with open(screenplay_path, "r", encoding="utf-8") as f:
        screenplay = f.read()
    dialogue = extract_dialogue(screenplay)
    if not dialogue:
        print("No dialogue found in the screenplay.")
        return
    synthesis_input = texttospeech.SynthesisInput(text=dialogue)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as out:
        out.write(response.audio_content)
    print(f"Voiceover saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a voiceover from a screenplay.")
    parser.add_argument("screenplay_path", help="Path to the screenplay file.")
    parser.add_argument("--project", required=True, help="Google Cloud project ID.")
    parser.add_argument(
        "--output_path",
        default="output/voiceover/voiceover.mp3",
        help="Path to save the generated voiceover.",
    )
    args = parser.parse_args()
    generate_voiceover(args.project, args.screenplay_path, args.output_path)