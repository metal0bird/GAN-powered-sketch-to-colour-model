from PIL import Image

def create_gif(folder_path, output_filename, duration=100, loop=0):

  frames = [Image.open(os.path.join(folder_path, image_file)) for image_file in os.listdir(folder_path) if image_file.lower().endswith((".jpg", ".jpeg", ".png"))]
  first_frame = frames[0]
  first_frame.save(output_filename, format="GIF", append_images=frames, save_all=True, duration=duration, loop=loop)

# Example usage
create_gif("progressV2", "animation.gif", duration=200, loop=1)
