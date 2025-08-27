
import argparse
import os
from google.cloud import texttospeech

def generate_voiceover(project_id: str, screenplay_path: str, output_path: str):
    """Generates a voiceover from a screenplay using Google Cloud Text-to-Speech."""

    # Initialize the Text-to-Speech client
    client = texttospeech.TextToSpeechClient()

    # Read the screenplay
    with open(screenplay_path, "r") as f:
        screenplay = f.read()

    # Extract dialogue from the screenplay (simple extraction logic)
    dialogue_lines = []
    for line in screenplay.split('\n'):
        if line.isupper() and not line.startswith('SCENE') and not line.startswith('INT.') and not line.startswith('EXT.'):
            # This is likely a character name
            pass
        elif line.startswith('('):
            # This is likely a parenthetical
            pass
        elif line.strip() and not line.isupper():
            dialogue_lines.append(line.strip())

    dialogue = " ".join(dialogue_lines)

    if not dialogue:
        print("No dialogue found in the screenplay.")
        return

    synthesis_input = texttospeech.SynthesisInput(text=dialogue)

    # Build the voice request
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )

    # Select the type of audio file you want
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    # Perform the text-to-speech request
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # Save the audio to the output file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(response.audio_content)

    print(f"Voiceover saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a voiceover from a screenplay.")
    parser.add_argument("screenplay_path", help="Path to the screenplay file.")
    parser.add_argument("--project", required=True, help="Google Cloud project ID.")
    parser.add_argument("--output_path", default="output/voiceover/voiceover.mp3", help="Path to save the generated voiceover.")
    args = parser.parse_args()

    generate_voiceover(args.project, args.screenplay_path, args.output_path)
