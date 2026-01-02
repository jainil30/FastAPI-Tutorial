
from urllib.parse import uses_params

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    session: AsyncSession = Depends(get_async_session)
):
    temp_file_path = None
    try:
        # Save uploaded file to temp
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        # Ensure UploadFile stream is closed early
        await file.close()

        # Open temp file with context manager for upload
        with open(temp_file_path, "rb") as f:
            upload_result = imagekit.files.upload(
                file=f,  # Pass the open file object directly
                file_name=file.filename,
                folder="/uploads",
                tags=["backend-upload"]
            )

        if upload_result.response_metadata.http_status_code == 200:
            post = Post(
                caption=caption,
                url=upload_result.url,
                file_type=upload_result.file_type,
                file_name=upload_result.name
            )
            session.add(post)
            await session.commit()
            await session.refresh(post)
            return post

        else:
            # If ImageKit returns non-200 (unlikely here, but safe)
            raise HTTPException(status_code=500, detail=f"Upload failed: {upload_result}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except PermissionError:
                # On Windows, file might still be locked briefly — ignore or log
                pass  # Temp files will be cleaned up eventually

"""
@app.post("/upload")
async def upload_file(
        file: UploadFile = File(...),
        caption: str = Form(""),
        session: AsyncSession = Depends(get_async_session)
):
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        upload_result  = imagekit.files.upload(
            file=open(temp_file_path,"rb"),
            file_name=file.filename,
            folder="/uploads",
            tags=["backend-upload"]
        )

        if upload_result.status_code == 200:
            post = Post(
                caption = caption,
                url = upload_result.url,
                file_type = upload_result.file_type,
                file_name = upload_result.name
            )

            session.add(post)
            await session.commit()
            await session.refresh(post)
            return post

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            file.file.close()
"""


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


"""
# text_posts = {1 : {"title" : "News Post" , "content" : "ABCD"}}
text_posts = {
    i: {
        "title": f"News Post {i}",
        "content": f"Dummy content for news post {i}"
    }
    for i in range(1, 51)
}


# @app.get("/hello")
# async def hello_world():
#     return {"message":"Hello World"}


@app.get("/posts")
async def get_all_posts(limit : int = None):
    if limit:
        return list(text_posts.values())[:limit]
    return text_posts

@app.get("/posts/{post_id}")
async def get_post(post_id: int) -> dict:
    if post_id not in text_posts.keys():
        raise HTTPException(status_code=404, detail="Post not found")
    return text_posts[post_id]

@app.post("/post")
async def create_post(post : PostCreate) -> PostResponse:
    new_post = {"title": post.title, "content": post.content}
    text_posts[max(text_posts.keys()) + 1] = new_post
    return new_post

"""