import argparse
import os
import subprocess

def assemble_film(clips_directory, output_filename):
    """Assembles video clips into a final film using FFmpeg."""
    print("Assembling the final film...")

    clips = sorted(
        [f for f in os.listdir(clips_directory) if f.endswith(".mp4")],
        key=lambda f: tuple(map(int, f.replace('.mp4', '').split('_')[1::2]))
    )

    if not clips:
        print("Error: No video clips found in the specified directory.")
        return

    file_list_path = os.path.join(clips_directory, "file_list.txt")
    with open(file_list_path, "w") as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")

    output_path = os.path.join("output", "final_film", output_filename)

    # Using subprocess to call ffmpeg
    ffmpeg_command = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", file_list_path,
        "-c", "copy",
        output_path
    ]

    try:
        subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
        print(f"\nFilm assembly complete. Final film saved to {output_path}")
    except FileNotFoundError:
        print("\nError: FFmpeg not found. Please make sure FFmpeg is installed and in your system's PATH.")
        print("You can download it from https://ffmpeg.org/download.html")
    except subprocess.CalledProcessError as e:
        print("\nError during FFmpeg execution:")
        print(e.stderr)
    finally:
        # Clean up the temporary file list
        os.remove(file_list_path)

def main():
    parser = argparse.ArgumentParser(description="Assemble video clips into a final film.")
    parser.add_argument("clips_directory", help="The directory containing the video clips.")
    parser.add_argument("output_filename", help="The filename for the final output film (e.g., my_film.mp4).")
    args = parser.parse_args()

    assemble_film(args.clips_directory, args.output_filename)

if __name__ == "__main__":
    main()
