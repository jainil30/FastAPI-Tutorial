from dotenv import load_dotenv
from imagekitio import ImageKit
import os

load_dotenv()
"""
IMAGE_PRIVATE_KEY=private_E4LnCOn2+8VEoBisxPjoEIkXp4Y=
IMAGE_PUBLIC_KEY=public_OGVxn7Wd7qOjLVQKKFDUX2rFJ2g=
IMAGE_URL=https://ik.imagekit.io/jainilDalwadi

"""
imagekit = ImageKit(
    private_key=os.getenv("IMAGE_PRIVATE_KEY"),
    base_url=os.getenv("IMAGE_URL")
)
