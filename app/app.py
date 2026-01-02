from fastapi import FastAPI, HTTPException, File, UploadFile, Depends, Form
from sqlalchemy.util.langhelpers import repr_tuple_names

from app.schemas import PostCreate, PostResponse
from app.db import Post,create_db_and_tables,get_async_session

from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select

from app.images import imagekit

import os
import shutil
import uuid
import tempfile
from app.cloudinary_config import cloudinary
import cloudinary.uploader


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/feed")
async def get_feed(
        session : AsyncSession = Depends(get_async_session)
):
    print("Checkpoint 1")
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = [row[0] for row in result.all()]
    print("Checkpoint 2")
    posts_data = []

    for post in posts:
        print("Checkpoint 3")
        posts_data.append({
            "id": str(post.id),
            "caption" : post.caption,
            "url" : post.url,
            "created_at" : post.created_at,
            "file_type" : post.file_type,
            "file_name" : post.file_name
        })
    print("Checkpoint 4")
    return posts_data

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    session: AsyncSession = Depends(get_async_session)
):
    temp_file_path = None
    try:
        # Save uploaded file to temp
        suffix = os.path.splitext(file.filename)[1] or ".jpg"  # fallback
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        # Close the UploadFile stream early
        await file.close()

        # Upload to Cloudinary (this handles everything securely)
        upload_result = cloudinary.uploader.upload(
            temp_file_path,
            folder="uploads",  # optional: organizes in your Media Library
            tags=["backend-upload"],
            resource_type="auto"  # auto-detects image/video/raw
        )

        # Cloudinary returns 200 + JSON on success
        post = Post(
            caption=caption,
            url=upload_result["secure_url"],  # HTTPS URL
            file_type=upload_result.get("resource_type", "image"),
            file_name=upload_result.get("original_filename", file.filename)
        )

        session.add(post)
        await session.commit()
        await session.refresh(post)
        return post

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except PermissionError:
                pass  # Windows lock - safe to ignore