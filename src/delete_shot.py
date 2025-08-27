import argparse
import os

def delete_shot(scene_number, shot_number):
    """Deletes a specific shot's image."""
    image_path = os.path.join("output", "visual_assets", f"scene_{scene_number}_shot_{shot_number}.png")
    try:
        os.remove(image_path)
        print(f"Deleted {image_path}")
    except FileNotFoundError:
        print(f"Error: {image_path} not found.")
    except Exception as e:
        print(f"Error deleting {image_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Delete a specific shot's image.")
    parser.add_argument("scene_number", type=int, help="The scene number of the shot to delete.")
    parser.add_argument("shot_number", type=int, help="The shot number of the shot to delete.")
    args = parser.parse_args()

    delete_shot(args.scene_number, args.shot_number)

if __name__ == "__main__":
    main()