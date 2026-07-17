import subprocess
import qrcode
from PIL import Image, ImageDraw, ImageFont

# Function to create the sticker image with QR code and text
def create_label(data_dict, img_path='label.png'):
    # Create a 600x300 pixel canvas
    img = Image.new('RGB', (600, 300), color='white')
    draw = ImageDraw.Draw(img)

    # Attempt to load fonts, fall back to default if necessary
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
        font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()

    # Draw Title
    draw.text((20, 10), "Your Personal ID Card", fill='black', font=font_title)

    # Draw Patient Details (Left side)
    details = f"{data_dict['first']} {data_dict['last']}\nID: {data_dict['id']}"
    draw.text((20, 200), details, fill='black', font=font_text)

    # Generate and Draw QR Code (Center)
    # The QR code contains only the patient ID, not the full patient data.
    qr_data = str(data_dict.get('id', ''))
    qr = qrcode.make(qr_data)
    qr = qr.resize((150, 150))
    img.paste(qr, (225, 80))

    # Save the generated label
    img.save(img_path)
    return img_path

# Function to print the label via CUPS
def print_label(img_path):
    printer_name = 'brotherql700'
    # Send to the specific printer using 'lp' command
    subprocess.run(['lp', '-d', printer_name, '-o', 'fit-to-page', img_path])
