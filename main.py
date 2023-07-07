import os
import time

from lavis.models import load_model_and_preprocess

from PIL import Image, ImageOps
import requests
import torch

import json
import io
import base64

import quart
import quart_cors
from quart import request, send_from_directory
from quart import jsonify

import openai

import meme_captioner

openai.api_key = ''
gpt_model = 'gpt-3.5-turbo'
blip2_model = 3
memes_per_request = 3
captions_per_request = 5

fake_mode = False

device = torch.device("cuda") if torch.cuda.is_available() else "cpu"
print("[BLIP 2] selected device:", device)

model_info = {
    0: ("blip2_opt", "pretrain_opt2.7b"),
    1: ("blip2_opt", "pretrain_opt6.7b"),
    2: ("blip2_opt", "caption_coco_opt2.7b"),
    3: ("blip2_opt", "caption_coco_opt6.7b"),
    4: ("blip2_t5", "pretrain_flant5xl"),
    5: ("blip2_t5", "caption_coco_flant5xl"),
    6: ("blip2_t5", "pretrain_flant5xxl"),
}

if blip2_model not in model_info:
    raise ValueError("[BLIP 2] Selected model does not exist:", blip2_model)

name, model_type = model_info[blip2_model]
print("[BLIP 2] selected model:", name, model_type)

if not fake_mode:
    model, vis_processors, _ = load_model_and_preprocess(
        name=name, model_type=model_type, is_eval=True, device=device
    )
    print("[BLIP 2] vis_processors keys:", vis_processors.keys())
else:
    model, vis_processors = None, None


def generate_caption_for_image(raw_image):
    if model is not None and not fake_mode:
        image = vis_processors["eval"](raw_image).unsqueeze(0).to(device)
        # due to the non-determinstic nature of necleus sampling, you may get different captions.
        return model.generate({"image": image}, use_nucleus_sampling=True, num_captions=captions_per_request)
    else:
        return ["a yellow box is sitting outside on a brick sidewalk",
                "a yellow postal box with a mail slot",
                "a package is sitting on top of a mailbox"]


def decode_image(base64_image):
    """Decode a base64 image to a PIL image."""
    # If base64_image is a data URL, remove the scheme
    if 'base64,' in base64_image:
        base64_image = base64_image.split('base64,')[1]

    # Decode the base64 string
    image_data = base64.b64decode(base64_image)

    # Create a BytesIO object and load the image data
    image = Image.open(io.BytesIO(image_data))

    # Apply orientation from EXIF data
    image = ImageOps.exif_transpose(image)

    return image


def encode_image(image):
    """Encode a PIL image to base64."""
    # Create a BytesIO object
    buffer = io.BytesIO()

    # Save the image to the BytesIO object
    image.save(buffer, format='JPEG')

    # Get the bytes of the saved image
    image_bytes = buffer.getvalue()

    # Encode the bytes to base64
    base64_image = base64.b64encode(image_bytes)

    # Convert the bytes to a string
    base64_image = base64_image.decode('utf-8')

    return base64_image


def generate_meme_from_caption(properties):
    if not fake_mode:
        return json.loads(openai.ChatCompletion.create(
            model=gpt_model,
            messages=[
                {"role": "system", "content": "You are a seasoned meme creator.\n" +
                                              "The user will upload an image on a meme generator website and describe it to you, including any relevant context.\n" +
                                              "Your task is to create a funny caption for the meme based on the user's description and any other parameters they provide. The caption MUST prioritize and incorporate the main elements mentioned in the description and especially the 'context'. If a specific style is requested, make sure to follow it.\n" +
                                              "To allow for the user to pick from multiple variants, your response should be a JSON array of " + str(
                    memes_per_request) + " objects. Each object must contain all keys specified in the \"requested_out_keys\" field. If multiple keys are requested, regard them as a single meme that is consistent in itself. The total length of all words in a single object (including all keys) must not exceed 20 words.\n" +
                                              "The caption must be based on the description and context provided by the user. Aim for humor, unless the user specifies otherwise.\n" +
                                              "Focus primarily on the elements included in the context and/or the most humorous ones."},
                {"role": "user", "content": json.dumps(properties)},
            ]
        ).choices[0].message.content)
    else:
        return [
            {"bottom_caption": "When your package is so excited to be delivered, it can't wait for you to open the"
                               " mailbox it can't wait for you to open the",
             "top_caption": "When your package is so excited to be delivered, it can't wait for you to open the"
                            " mailbox it can't wait for you to open the"},
            {"bottom_caption": "When you order a package online and want to make sure your mailbox gets the message"},
            {"bottom_caption": "When you trust your package to arrive at 10"}
        ]


app = quart_cors.cors(quart.Quart(__name__), allow_origin="*")


@app.route("/")
async def index():
    return await send_from_directory("", "index.html")

@app.route("/doc/img/icon-transparent.png")
async def icon_transparent():
    return await send_from_directory("doc/img", "icon-transparent.png")


@app.route("/memegen/generate", methods=['POST'])
async def post_generate_meme_from_caption():
    data = json.loads((await request.get_data()).decode('utf-8'))

    base64img = data.get("base64img")
    language = data.get("language")
    style = data.get("style")
    context = data.get("context")

    meme_type = data.get("meme_type")
    if meme_type == 1 or meme_type == "1":
        requested_out_keys = ["top_caption"]
    elif meme_type == 2 or meme_type == "2":
        requested_out_keys = ["top_caption", "bottom_caption"]
    elif meme_type == 3 or meme_type == "3":
        requested_out_keys = ["bottom_caption"]
    else:
        requested_out_keys = ["top_caption"]

    print("generating meme for", context, style, language, requested_out_keys)

    img = decode_image(base64img)
    img = scale_image(img)

    captions = generate_caption_for_image(img)
    description = json.dumps(captions)

    print("caption generated for image", json.dumps(captions))

    request_data = {
        "description": description,
        "language": language,
        "style": style,
        "context": context,
        "requested_out_keys": requested_out_keys
    }
    request_data = trim_string_fields(request_data)

    captions = generate_meme_from_caption(request_data)
    captions = captions[:memes_per_request]

    print("captions for the meme", json.dumps(captions))

    current_time_millis = int(time.time() * 1000)
    ensure_output_dir_exists()

    captioned_images = []
    for i, caption in enumerate(captions):
        output_image = meme_captioner.add_text_to_image_for_meme_caption(img.copy(), caption)
        output_image = meme_captioner.add_watermark(output_image)
        output_image.save(f'output/{current_time_millis}-{i}.png')
        captioned_images.append(encode_image(output_image))

    return jsonify(captioned_images)


def ensure_output_dir_exists():
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)


def trim_string_fields(data):
    for key, value in data.items():
        if isinstance(value, str):
            data[key] = value[:300]
    return data


def scale_image(image):
    """Resize and crop a PIL image to a centered square with maximum dimensions of 1000x1000 pixels."""
    width, height = image.size  # Get image dimensions

    # Determine the smaller dimension
    min_dim = min(width, height)

    # Calculate the scaling factor
    scale_factor = 1000.0 / min_dim

    # Resize the image so that the smaller dimension fits 1000 pixels
    new_width = int(scale_factor * width)
    new_height = int(scale_factor * height)
    image = image.resize((new_width, new_height), Image.LANCZOS)

    # Determine dimensions of the square
    max_dim = 1000  # Limit the maximum dimension to 1000 pixels

    # Calculate the left, top, right, and bottom coordinates for the crop box
    left = (new_width - max_dim) / 2
    top = (new_height - max_dim) / 2
    right = (new_width + max_dim) / 2
    bottom = (new_height + max_dim) / 2

    # Crop the image to the crop box
    image = image.crop((left, top, right, bottom))

    return image


def main():
    app.run(debug=True, host="0.0.0.0", port=5003)


if __name__ == "__main__":
    main()
