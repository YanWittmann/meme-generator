# AI Meme Generator

A meme generator using BLIP 2 and OpenAi's GPT Models.

## Process:

1. Receive request via quarkus endpoint
2. Use torch on CUDA to run a BLIP 2 model to generate a caption for the image
3. Send to OpenAi's API with a request to generate a meme from the caption with given parameters
4. Add caption to initial image
5. Complete request by sending images back to user
