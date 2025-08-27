
import argparse
import os
import ffmpeg

def assemble_film(
    video_clips_dir: str,
    soundtrack_path: str,
    voiceover_path: str,
    output_path: str,
    output_filename: str
):
    """Assembles the final film from video clips, soundtrack, and voiceover."""

    # Get all video clips and sort them
    video_files = sorted([f for f in os.listdir(video_clips_dir) if f.endswith(".mp4")])
    video_paths = [os.path.join(video_clips_dir, f) for f in video_files]

    if not video_paths:
        print("No video clips found.")
        return

    # Create a temporary file with the list of video files for concatenation
    concat_file_path = os.path.join(video_clips_dir, "concat.txt")
    with open(concat_file_path, "w") as f:
        for path in video_paths:
            f.write(f"file '{os.path.basename(path)}'\n")

    # Concatenate video clips
    video_stream = ffmpeg.input(concat_file_path, format='concat', safe=0, r=24)

    # Input soundtrack and voiceover
    soundtrack_stream = ffmpeg.input(soundtrack_path)
    voiceover_stream = ffmpeg.input(voiceover_path)

    # Combine audio streams
    combined_audio = ffmpeg.filter([
        soundtrack_stream, 
        voiceover_stream
    ], 'amix', inputs=2, duration='first')

    # Create the output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    final_output_path = os.path.join(output_path, output_filename)

    # Mux video and combined audio
    ( 
        ffmpeg
        .output(video_stream, combined_audio, final_output_path, vcodec='copy', acodec='aac', shortest=None)
        .run(overwrite_output=True)
    )

    # Clean up the temporary concat file
    os.remove(concat_file_path)

    print(f"Final film assembled at {final_output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assemble the final film.")
    parser.add_argument("video_clips_dir", help="Directory containing the video clips.")
    parser.add_argument("soundtrack_path", help="Path to the soundtrack file.")
    parser.add_argument("voiceover_path", help="Path to the voiceover file.")
    parser.add_argument("output_path", help="Directory to save the final film.")
    parser.add_argument("output_filename", help="Filename of the final film.")
    args = parser.parse_args()

    assemble_film(
        args.video_clips_dir, 
        args.soundtrack_path, 
        args.voiceover_path, 
        args.output_path, 
        args.output_filename
    )
