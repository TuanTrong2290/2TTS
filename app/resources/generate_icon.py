#!/usr/bin/env python3
"""Generate application icons for 2TTS

This script generates PNG and ICO icons for the 2TTS application.
Requires: pillow

Usage: python generate_icon.py
"""

import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installing Pillow...")
    os.system("pip install pillow")
    from PIL import Image, ImageDraw, ImageFont


def create_2tts_icon(size: int = 256) -> Image.Image:
    """Create a 2TTS branded icon"""
    # Create image with gradient background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw rounded rectangle background with gradient effect
    padding = size // 16
    corner_radius = size // 6
    
    # Main background - dark blue gradient effect
    for i in range(size):
        ratio = i / size
        r = int(30 + ratio * 20)
        g = int(60 + ratio * 40)
        b = int(120 + ratio * 60)
        draw.line([(0, i), (size, i)], fill=(r, g, b, 255))
    
    # Draw rounded rectangle mask
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=corner_radius,
        fill=255
    )
    
    # Apply mask to create rounded corners
    background = img.copy()
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    img.paste(background, mask=mask)
    draw = ImageDraw.Draw(img)
    
    # Draw "2TTS" text
    try:
        font_size = size // 4
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    text = "2TTS"
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center text
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - size // 10
    
    # Draw text shadow
    draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 100))
    
    # Draw main text
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    
    # Draw sound wave icon
    wave_y = y + text_height + size // 10
    wave_center_x = size // 2
    wave_height = size // 8
    wave_color = (100, 200, 255, 255)
    
    # Draw simple sound wave bars
    bar_width = size // 20
    bar_spacing = size // 12
    bars = [0.3, 0.6, 1.0, 0.7, 0.4]
    
    for i, height_ratio in enumerate(bars):
        bar_x = wave_center_x + (i - 2) * bar_spacing - bar_width // 2
        bar_height = int(wave_height * height_ratio)
        bar_y1 = wave_y - bar_height // 2
        bar_y2 = wave_y + bar_height // 2
        
        draw.rounded_rectangle(
            [bar_x, bar_y1, bar_x + bar_width, bar_y2],
            radius=bar_width // 2,
            fill=wave_color
        )
    
    return img


def save_icons(output_dir: Path):
    """Save icons in various formats and sizes"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate main icon
    icon_256 = create_2tts_icon(256)
    
    # Save PNG versions
    icon_256.save(output_dir / "icon.png", "PNG")
    print(f"Created: {output_dir / 'icon.png'}")
    
    # Create ICO file with multiple sizes
    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = []
    
    for size in sizes:
        resized = icon_256.resize((size, size), Image.Resampling.LANCZOS)
        icons.append(resized)
    
    # Save ICO file
    icon_256.save(
        output_dir / "icon.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes]
    )
    print(f"Created: {output_dir / 'icon.ico'}")
    
    # Save additional PNG sizes
    for size in [16, 32, 48, 64, 128]:
        resized = icon_256.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(output_dir / f"icon_{size}.png", "PNG")
        print(f"Created: {output_dir / f'icon_{size}.png'}")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    save_icons(script_dir)
    print("\nIcon generation complete!")
