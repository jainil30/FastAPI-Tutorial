import streamlit as st
import requests
import urllib.parse

st.set_page_config(page_title="Simple Social", layout="wide")

# Initialize session state
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user' not in st.session_state:
    st.session_state.user = None


def get_headers():
    """Get authorization headers with token"""
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


def login_page():
    st.title("🚀 Welcome to Simple Social")

    email = st.text_input("Email:")
    password = st.text_input("Password:", type="password")

    if email and password:
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Login", type="primary", use_container_width=True):
                login_data = {"username": email, "password": password}
                response = requests.post("http://localhost:8000/auth/jwt/login", data=login_data)

                if response.status_code == 200:
                    token_data = response.json()
                    st.session_state.token = token_data["access_token"]

                    user_response = requests.get("http://localhost:8000/auth/me", headers=get_headers())
                    if user_response.status_code == 200:
                        st.session_state.user = user_response.json()
                        st.rerun()
                    else:
                        st.error("Failed to get user info")
                else:
                    st.error("Invalid email or password!")

        with col2:
            if st.button("Sign Up", type="secondary", use_container_width=True):
                signup_data = {"email": email, "password": password}
                response = requests.post("http://localhost:8000/auth/register", json=signup_data)

                if response.status_code == 201:
                    st.success("Account created! Click Login now.")
                else:
                    error_detail = response.json().get("detail", "Registration failed")
                    st.error(f"Registration failed: {error_detail}")
    else:
        st.info("Enter your email and password above")


def upload_page():
    st.title("📸 Share Something")

    uploaded_file = st.file_uploader("Choose media", type=['png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov', 'mkv', 'webm'])
    caption = st.text_area("Caption:", placeholder="What's on your mind?")

    if uploaded_file and st.button("Share", type="primary"):
        with st.spinner("Uploading to Cloudinary..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {"caption": caption}
            response = requests.post("http://localhost:8000/upload", files=files, data=data, headers=get_headers())

            if response.status_code == 200:
                st.success("Posted successfully!")
                st.rerun()
            else:
                try:
                    error_msg = response.json().get("detail", "Upload failed")
                except:
                    error_msg = response.text
                st.error(f"Upload failed: {error_msg}")


def get_cloudinary_image_url(base_url, caption=None, width=800):
    """
    Generate a Cloudinary transformed URL with optional caption overlay
    """
    transformations = []

    # Resize to fixed width, maintain aspect ratio
    transformations.append(f"w_{width}")

    # Auto quality and format
    transformations.append("q_auto")
    transformations.append("f_auto")

    # Add caption overlay at bottom if provided
    if caption:
        encoded_caption = urllib.parse.quote(caption)
        overlay = f"l_text:Arial_48_bold:{encoded_caption},co_white,bo_6px_solid_black,g_south,y_20"
        transformations.append(overlay)

    # Combine transformations
    transform_str = ",".join(transformations)
    return base_url.replace("/upload/", f"/upload/{transform_str}/")


def get_cloudinary_video_url(base_url, width=800):
    """
    Generate video URL with poster thumbnail and optimizations
    """
    transformations = f"w_{width},q_auto,f_auto"
    return base_url.replace("/upload/", f"/upload/{transformations}/")


def feed_page():
    st.title("🏠 Feed")

    response = requests.get("http://localhost:8000/feed", headers=get_headers())
    if response.status_code != 200:
        st.error("Failed to load feed. Make sure you're logged in.")
        return

    data = response.json()
    posts = data if isinstance(data, list) else data.get("posts", [])

    if not posts:
        st.info("No posts yet! Be the first to share something.")
        return

    for post in posts:
        st.markdown("---")

        # Header: email + date + delete button
        col1, col2 = st.columns([4, 1])
        with col1:
            created_date = post['created_at'][:10] if post['created_at'] else "Unknown date"
            st.markdown(f"**{post.get('email', 'Unknown')}** • {created_date}")
        with col2:
            if post.get('is_owner', False):
                if st.button("🗑️", key=f"delete_{post['id']}", help="Delete your post"):
                    del_response = requests.delete(
                        f"http://localhost:8000/posts/{post['id']}",
                        headers=get_headers()
                    )
                    if del_response.status_code == 200:
                        st.success("Post deleted!")
                        st.rerun()
                    else:
                        st.error("Failed to delete post")

        caption = post.get('caption', '').strip()

        if post['file_type'] == 'image':
            img_url = get_cloudinary_image_url(post['url'], caption=caption if caption else None, width=800)
            st.image(img_url, use_column_width=True)
            if caption and len(caption) > 50:  # Show long captions below if not overlaid well
                st.caption(caption)
        else:
            # Video
            video_url = get_cloudinary_video_url(post['url'], width=800)
            st.video(video_url)
            if caption:
                st.caption(caption)

        st.markdown("<br>", unsafe_allow_html=True)  # spacing


# Main app routing
if st.session_state.user is None:
    login_page()
else:
    st.sidebar.title(f"👋 Hi {st.session_state.user['email']}!")

    if st.sidebar.button("Logout"):
        st.session_state.token = None
        st.session_state.user = None
        st.rerun()

    st.sidebar.markdown("---")
    page = st.sidebar.radio("Navigate", ["🏠 Feed", "📸 Upload"])

    if page == "🏠 Feed":
        feed_page()
    elif page == "📸 Upload":
        upload_page()