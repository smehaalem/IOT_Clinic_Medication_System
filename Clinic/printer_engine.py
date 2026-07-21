import subprocess
import qrcode
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont


# Function to create the sticker image with QR code and text
def create_label(data_dict, img_path='label.png'):
    # Design the label layout horizontally (530 width x 380 height)
    # Perfectly suited for the 53mm length specification and 62mm roll stock
    horizontal_img = Image.new('RGB', (530, 380), color='white')
    draw = ImageDraw.Draw(horizontal_img)

    # Attempt to load fonts, fall back to default if necessary
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
        font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()

    # Draw Title (Top left region)
    draw.text((25, 25), "Personal ID Card", fill='black', font=font_title)

    # Draw Patient Details (Left side - maximum room up to x=320)
    details = f"Patient: {data_dict['first']} {data_dict['last']}\nID: {data_dict['id']}"
    draw.text((25, 115), details, fill='black', font=font_text)

    # Generate and Draw QR Code
    # FIXED: The QR code now contains ONLY the raw patient ID string (no JSON formatting)
    qr_data = str(data_dict['id'])
    qr = qrcode.make(qr_data)
    qr = qr.resize((170, 170))
    horizontal_img.paste(qr, (330, 170))

    # Rotate the entire canvas by 90 degrees counter-clockwise
    # This transforms the 530x380 horizontal layout into a 380x530 portrait feed for the printer
    final_img = horizontal_img.rotate(90, expand=True)

    # Save the rotated label
    final_img.save(img_path)
    return img_path


# Function to print the label via CUPS
def print_label(img_path):
    printer_name = 'brotherql700'
    # Send cleanly to the printer using default settings
    subprocess.run(['lp', '-d', printer_name, img_path])