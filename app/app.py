from fastapi import FastAPI, HTTPException, File, UploadFile, Depends, Form
from sqlalchemy.sql.functions import user
from sqlalchemy.util.langhelpers import repr_tuple_names

from app.schemas import PostCreate, PostResponse, UserUpdate,UserRead,UserCreate
from app.db import Post,create_db_and_tables,get_async_session

from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select, result_tuple

from app.images import imagekit

import os
import shutil
import uuid
import tempfile
from app.cloudinary_config import cloudinary
import cloudinary.uploader

from app.users import auth_backend, current_active_users, fastapi_users,User

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/auth", tags=["auth"])


@app.get("/feed")
async def get_feed(
        user : User = Depends(current_active_users),
        session : AsyncSession = Depends(get_async_session)
):
    print("Checkpoint 1")
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = [row[0] for row in result.all()]

    result = await session.execute(select(User))
    users = [row[0] for row in result.all()]
    user_dict = {u.id: u.email for u in users}

    print("Checkpoint 2")
    posts_data = []

    for post in posts:
        print("Checkpoint 3")
        posts_data.append({
            "id": str(post.id),
            "user_id": str(post.user_id),
            "caption" : post.caption,
            "url" : post.url,
            "created_at" : post.created_at,
            "file_type" : post.file_type,
            "file_name" : post.file_name,
            "is_owner" : post.user_id == user.id,
            "email" : user_dict.get(post.user_id,"Unknown"),
        })
    print("Checkpoint 4")
    return posts_data

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    user : User = Depends(current_active_users),
    session: AsyncSession = Depends(get_async_session)
):
    temp_file_path = None
    try:
        suffix = os.path.splitext(file.filename)[1] or ".jpg"  # fallback
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)


        await file.close()

        upload_result = cloudinary.uploader.upload(
            temp_file_path,
            folder="uploads",
            tags=["backend-upload"],
            resource_type="auto"
        )


        post = Post(
            user_id = user.id,
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
                pass

@app.delete("/posts/{post_id}")
async def delete_post(
        post_id:str ,
        user : User = Depends(current_active_users),
        session: AsyncSession = Depends(get_async_session)):
    try:
        post_uuid = uuid.UUID(post_id)

        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().one()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        if post.user_id != user.id:
            raise HTTPException(status_code=403, detail="You are not allowed to delete this post")

        await session.delete(post)
        await session.commit()

        return {"success": True, "message": "Post Deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


