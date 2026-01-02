from fastapi import FastAPI,HTTPException
from app.schemas import PostCreate, PostResponse
from app.db import Post,create_db_and_tables,get_async_session

from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

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

