from PIL import Image
import os

def crop_images(folder_path, crop_box, output_folder=None, overwrite=False):

  for filename in os.listdir(folder_path):
    if filename.lower().endswith((".jpg", ".jpeg", ".png")):
      image_path = os.path.join(folder_path, filename)
      img = Image.open(image_path)
      cropped_img = img.crop(crop_box)
      
      if output_folder:
        new_filename = filename
        output_path = os.path.join(output_folder, new_filename)
      else:
        base, ext = os.path.splitext(filename)
        new_filename = f"{base}_cropped{ext}"
        output_path = os.path.join(folder_path, new_filename)
      
      if not os.path.exists(output_path) or overwrite:
        cropped_img.save(output_path)
        print(f"Image '{filename}' cropped and saved to '{output_path}'.")

# Example usage
folder_path = "progressV2"
crop_box = (150, 400, 1400, 1100)  # Left, Top, Right, Bottom
output_folder = "cropped_images"  # Optional, defaults to original folder
overwrite = True  # Optional, defaults to False

crop_images(folder_path, crop_box, output_folder, overwrite)
