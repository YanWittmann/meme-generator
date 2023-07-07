from PIL import Image, ImageDraw, ImageFont
import textwrap

import math


# from scipy.optimize import curve_fit

def fitting_function(X, a, b, c):
    return a * (X + c) ** b


# X = [40, 83, 206]
# y = [137, 77, 62]
#
# # Perform the curve fit
# params, params_covariance = curve_fit(fitting_function, X, y)
#
# print("params", params)
# print("plottable function",
#       "y = " + str(round(params[0], 2)) + " * (x + " + str(round(params[2], 2)) + ")^" + str(round(params[1], 2)))

params = [142.86105262, -0.16304286, -38.70703769]  # pre-fitted parameters


def generate_font(image_width, caption_length):
    caption_length = max(40, caption_length)  # Minimum caption length of 20 characters

    # Fitted parameters
    a = params[0]
    b = params[1]
    c = params[2]

    # Power law scaling with caption length
    base_font_size = max(10, int(fitting_function(caption_length, a, b, c)))

    font_size = int(base_font_size * image_width / 1000)  # Linear scaling with image width

    return ImageFont.truetype("impact.ttf", size=font_size)


def add_text_to_image_for_meme_caption(image, caption):
    length_top = len(caption.get('top_caption', ''))
    length_bottom = len(caption.get('bottom_caption', ''))
    if length_top > 0 and length_bottom > 0:
        max_caption_length = (length_top + length_bottom) / 1.2
    else:
        max_caption_length = max(length_top, length_bottom)

    font = generate_font(image.width, max_caption_length)

    # Create ImageDraw object
    draw = ImageDraw.Draw(image)

    # Define text color and stroke
    text_color = "white"
    stroke_color = "black"
    stroke_width = int(font.size * 0.1)  # Stroke width is 10% of font size

    # Calculate maximum line width in characters
    max_line_width = int(image.width / font.size * 2.2)

    # Add top text
    if 'top_caption' in caption:
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
        y_text = image.height - image.width * 0.02
        for line in reversed(lines):
            line_width, line_height = draw.textsize(line, font=font)
            x_line = (image.width - line_width) / 2
            y_text -= line_height
            draw.text((x_line, y_text), line, fill=text_color, font=font, stroke_width=stroke_width,
                      stroke_fill=stroke_color)

    return image


def add_watermark(image):
    watermark = Image.open("doc/img/watermark.png").convert("RGBA")
    watermark_size = int(image.width * 0.06)
    padding = int(image.width * 0.01)
    watermark = watermark.resize((watermark_size, watermark_size))
    watermark_position = (image.width - watermark_size - padding, image.height - watermark_size - padding)
    image_with_watermark = image.copy()
    image_with_watermark.paste(watermark, watermark_position, watermark)
    return image_with_watermark
