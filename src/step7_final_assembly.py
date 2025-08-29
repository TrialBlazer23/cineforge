
import argparse
import os
import ffmpeg
import re

def assemble_film(
    video_clips_dir: str,
    dialogue_dir: str,
    soundtrack_dir: str,
    output_dir: str,
    output_filename: str
):
    """Assembles the final film from video clips, dialogue, and soundtracks."""

    video_files = sorted([f for f in os.listdir(video_clips_dir) if f.endswith(".mp4")])
    all_dialogue_files = sorted([f for f in os.listdir(dialogue_dir) if f.endswith(".mp3")])
    soundtrack_files = sorted([f for f in os.listdir(soundtrack_dir) if f.endswith(".mp3")])

    if not video_files:
        print("No video clips found.")
        return

    processed_scene_files = []
    temp_dir = os.path.join(output_dir, "temp_scenes")
    os.makedirs(temp_dir, exist_ok=True)

    for i, video_file in enumerate(video_files):
        scene_num = i + 1
        video_path = os.path.join(video_clips_dir, video_file)
        video_input = ffmpeg.input(video_path)

        # Filter dialogue files for the current scene
        scene_dialogue_files = [f for f in all_dialogue_files if re.match(f'scene_{scene_num}_dialogue_\d{{3}}\.mp3', f)]
        
        if scene_dialogue_files:
            dialogue_inputs = [ffmpeg.input(os.path.join(dialogue_dir, f)) for f in scene_dialogue_files]
            concatenated_dialogue = ffmpeg.concat(*dialogue_inputs, v=0, a=1)
        else:
            concatenated_dialogue = None

        # Get soundtrack for the scene
        soundtrack_path = os.path.join(soundtrack_dir, f"scene_{scene_num:03d}_soundtrack.mp3")
        if os.path.exists(soundtrack_path):
            soundtrack_input = ffmpeg.input(soundtrack_path)
        else:
            soundtrack_input = None

        # Combine audio
        if concatenated_dialogue and soundtrack_input:
            # With audio ducking
            combined_audio = ffmpeg.filter_complex(
                [
                    soundtrack_input.audio,
                    concatenated_dialogue.audio
                ],
                "[0]volume=0.3[a0];[1]volume=1.0[a1];[a0][a1]amix=inputs=2:duration=first[a]"
            )
        elif concatenated_dialogue:
            combined_audio = concatenated_dialogue.audio
        elif soundtrack_input:
            combined_audio = soundtrack_input.audio
        else:
            combined_audio = None

        # Mux video and audio
        output_path = os.path.join(temp_dir, f"scene_{scene_num:03d}.mp4")
        if combined_audio:
            (ffmpeg.output(video_input.video, combined_audio, output_path, vcodec='copy', acodec='aac', shortest=None)
             .run(overwrite_output=True))
        else:
            (ffmpeg.output(video_input.video, output_path, vcodec='copy')
             .run(overwrite_output=True))
        processed_scene_files.append(output_path)

    # Concatenate all processed scenes
    if processed_scene_files:
        concat_file_path = os.path.join(output_dir, "concat.txt") # Changed to output_dir
        with open(concat_file_path, "w") as f:
            for path in processed_scene_files:
                f.write(f"file '{os.path.basename(path)}'\n")

        final_output_path = os.path.join(output_dir, output_filename)
        (ffmpeg.input(concat_file_path, format='concat', safe=0)
         .output(final_output_path, c='copy').run(overwrite_output=True))

        print(f"Final film assembled at {final_output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assemble the final film from scenes, dialogue, and soundtracks.")
    parser.add_argument("--video_clips_dir", required=True, help="Directory containing the video clips.")
    parser.add_argument("--dialogue_dir", required=True, help="Directory containing the dialogue audio files.")
    parser.add_argument("--soundtrack_dir", required=True, help="Directory containing the soundtrack audio files.")
    parser.add_argument("--output_dir", default="output/final_film", help="Directory to save the final film.")
    parser.add_argument("--output_filename", default="final_film.mp4", help="Filename of the final film.")
    args = parser.parse_args()

    assemble_film(
        args.video_clips_dir,
        args.dialogue_dir,
        args.soundtrack_dir,
        args.output_dir,
        args.output_filename
    )
