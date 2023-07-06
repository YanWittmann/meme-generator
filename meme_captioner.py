from PIL import Image, ImageDraw, ImageFont
import textwrap


def add_text_to_image_for_meme_caption(image, caption, text_width_proportion=2):
    # Calculate font size as a proportion of image width
    font_size = int(image.width * 0.08)  # 5% of image width

    # Load a TrueType or OpenType font file, and create a font object.
    font = ImageFont.truetype("impact.ttf", size=font_size)

    # Create ImageDraw object
    draw = ImageDraw.Draw(image)

    # Define text color and stroke
    text_color = "white"
    stroke_color = "black"
    stroke_width = int(font_size * 0.1)  # Stroke width is 10% of font size

    # Calculate maximum line width in characters
    max_line_width = int(image.width / font_size * text_width_proportion)

    # Add top text
    top_text = caption.get('top_caption', '')
    lines = textwrap.wrap(top_text, width=max_line_width)
    y_text = 5
    for line in lines:
        line_width, line_height = draw.textsize(line, font=font)
        x_line = (image.width - line_width) / 2
        draw.text((x_line, y_text), line, fill=text_color, font=font, stroke_width=stroke_width,
                  stroke_fill=stroke_color)
        y_text += line_height

    # Add bottom text if it exists
    if 'bottom_caption' in caption:
        bottom_text = caption['bottom_caption']
        lines = textwrap.wrap(bottom_text, width=max_line_width)
        y_text = image.height - 10
        for line in reversed(lines):
            line_width, line_height = draw.textsize(line, font=font)
            x_line = (image.width - line_width) / 2
            y_text -= line_height
            draw.text((x_line, y_text), line, fill=text_color, font=font, stroke_width=stroke_width,
                      stroke_fill=stroke_color)

    return image
