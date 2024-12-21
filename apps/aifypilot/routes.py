# -*- encoding: utf-8 -*-
"""
Routes for the aifypilot blueprint, extended with images, videos, Twitter, and Reddit sources.
"""

from flask import Blueprint, request, jsonify, render_template
import os
import base64
from io import BytesIO
import matplotlib.pyplot as plt
from PIL import Image
import requests
import yfinance as yf
from langchain.chains import RetrievalQA
from . import vector_store, text_splitter, wiki_wiki, llm

blueprint = Blueprint(
    'aifypilot_blueprint',
    __name__,
    url_prefix=''
)

@blueprint.before_app_first_request
def ensure_directories():
    # Ensure the directories exist before handling requests
    blueprint.root_path = blueprint.root_path or '.'
    upload_folder = os.path.join(blueprint.root_path, 'uploads')
    image_folder = os.path.join(blueprint.root_path, 'uploaded_images')
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(image_folder, exist_ok=True)

@blueprint.route("/add_website", methods=["POST"])
def add_website():
    data = request.json
    url = data.get("url", "")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        response = requests.get(url)
        response.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([para.get_text() for para in paragraphs])
        docs = text_splitter.split_text(text)
        vector_store.add_texts(docs)
        return jsonify({"message": f"Website '{url}' content indexed successfully.", "extracted_pages": docs})
    except Exception as e:
        return jsonify({"error": f"Error scraping {url}: {str(e)}"}), 400

@blueprint.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    upload_folder = os.path.join(blueprint.root_path, 'uploads')
    file_path = os.path.join(upload_folder, file.filename)
    file.save(file_path)

    from tika import parser
    try:
        extracted_text = parser.from_file(file_path).get("content", "")
        if not extracted_text:
            return jsonify({"error": "Failed to extract text from the file"}), 400

        docs = text_splitter.split_text(extracted_text)
        vector_store.add_texts(docs)
        return jsonify({"message": f"File '{file.filename}' processed and indexed successfully.", "extracted_pages": docs})
    except Exception as e:
        return jsonify({"error": f"File processing failed: {str(e)}"}), 500

@blueprint.route("/chart", methods=["POST"])
def generate_chart():
    data = request.json
    ticker = data.get("ticker", "")
    if not ticker:
        return jsonify({"error": "Ticker symbol required"}), 400

    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period="1mo")
        plt.figure(figsize=(10, 5))
        plt.plot(history.index, history['Close'], label="Close Price")
        plt.title(f"{ticker.upper()} Stock Prices")
        plt.xlabel("Date")
        plt.ylabel("Price (USD)")
        plt.legend()
        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        chart_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        buf.close()
        return jsonify({"chart": chart_base64})
    except Exception as e:
        return jsonify({"error": f"Error fetching data for {ticker}: {str(e)}"}), 400

@blueprint.route("/analyze_image", methods=["POST"])
def analyze_image():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image = request.files["image"]
    if image.filename == "":
        return jsonify({"error": "No selected image"}), 400

    image_folder = os.path.join(blueprint.root_path, 'uploaded_images')
    file_path = os.path.join(image_folder, image.filename)
    image.save(file_path)

    try:
        img = Image.open(file_path)
        img = img.convert("RGB")
        img.save(file_path)
        # Placeholder for image analysis
        response = {"dummy_response": "Analysis not implemented"}
        return jsonify({"analysis": response})
    except Exception as e:
        return jsonify({"error": f"Image analysis failed: {str(e)}"}), 500

@blueprint.route("/query", methods=["POST"])
def query_endpoint():
    data = request.json
    query = data.get("query", "")
    source = data.get("source", "files")
    if not query:
        return jsonify({"error": "No query provided"}), 400

    # Query from our vector store
    if source == "files":
        retriever = vector_store.as_retriever()
        qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever, return_source_documents=True)
        qa_result = qa_chain({"query": query})
        response = qa_result["result"]
        source_docs = qa_result.get("source_documents", [])
        source_texts = [doc.page_content for doc in source_docs]
        return jsonify({"response": response, "sources": source_texts})

    # Wikipedia search
    elif source == "wikipedia":
        page = wiki_wiki.page(query)
        if not page.exists():
            return jsonify({"error": f"No Wikipedia page found for '{query}'"}), 404
        response = page.summary
        return jsonify({"response": response, "title": page.title, "url": page.fullurl})

    # News (Financial News)
    elif source == "news":
        url = data.get("url", "")
        if not url:
            return jsonify({"error": "News URL required"}), 400
        try:
            r = requests.get(url)
            r.raise_for_status()
            text = r.text
            snippet = text[:500] + "..." if len(text) > 500 else text
            return jsonify({"response": "Content fetched from URL", "snippet": snippet})
        except Exception as e:
            return jsonify({"error": f"Error fetching news from {url}: {str(e)}"}), 400

    # Stock Data: Summarize stock info
    elif source == "stock":
        ticker = data.get("ticker", "")
        if not ticker:
            return jsonify({"error": "Ticker symbol required"}), 400
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            response = f"{ticker.upper()} Info: {info.get('longName', 'N/A')} - {info.get('regularMarketPrice', 'N/A')} USD"
            return jsonify({"response": response})
        except Exception as e:
            return jsonify({"error": f"Error fetching data for {ticker}: {str(e)}"}), 400

    # DuckDuckGo search with image support
    elif source == "duckduckgo":
        ddg_url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_redirect": "1", "no_html": "1"}
        try:
            ddg_response = requests.get(ddg_url, params=params)
            ddg_response.raise_for_status()
            ddg_data = ddg_response.json()
            response = ddg_data.get('AbstractText', '')
            img_url = ddg_data.get('Image', '')
            if not response:
                # If no direct abstract, try related topics
                related_topics = ddg_data.get('RelatedTopics', [])
                if related_topics:
                    rt = related_topics[0]
                    response = rt.get('Text', 'No results found.')
                    # Try to get image from related topic if main image not found
                    if not img_url:
                        icon = rt.get('Icon', {})
                        img_url = icon.get('URL', '')
                else:
                    response = "No results found."
            return jsonify({"response": response, "image": img_url if img_url else None})
        except Exception as e:
            return jsonify({"error": f"DuckDuckGo search failed: {str(e)}"}), 500

    # YouTube search for a video
    elif source == "youtube":
        # You need a YouTube Data API key.
        youtube_api_key = "YOUR_YOUTUBE_API_KEY"
        youtube_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "key": youtube_api_key,
            "maxResults": 1
        }
        try:
            yt_response = requests.get(youtube_url, params=params)
            yt_response.raise_for_status()
            yt_data = yt_response.json()
            items = yt_data.get("items", [])
            if not items:
                return jsonify({"response": "No videos found."})
            video = items[0]
            video_id = video["id"]["videoId"]
            title = video["snippet"]["title"]
            channel_title = video["snippet"]["channelTitle"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            return jsonify({"response": f"Found video: {title} by {channel_title}", "video_url": video_url})
        except Exception as e:
            return jsonify({"error": f"YouTube search failed: {str(e)}"}), 500

    # Twitter search for tweets
    elif source == "twitter":
        # Use Twitter Bearer Token from your environment or config
        bearer_token = "YOUR_TWITTER_BEARER_TOKEN"
        twitter_url = "https://api.twitter.com/2/tweets/search/recent"
        headers = {"Authorization": f"Bearer {bearer_token}"}
        params = {
            "query": query,
            "max_results": 5,  # get up to 5 tweets
            "tweet.fields": "text,author_id,created_at"
        }
        try:
            tw_response = requests.get(twitter_url, headers=headers, params=params)
            tw_response.raise_for_status()
            tw_data = tw_response.json()
            tweets = tw_data.get("data", [])
            if not tweets:
                return jsonify({"response": "No tweets found."})
            # Return a list of tweets
            tweet_texts = [t["text"] for t in tweets]
            return jsonify({"response": f"Found {len(tweets)} tweets.", "tweets": tweet_texts})
        except Exception as e:
            return jsonify({"error": f"Twitter search failed: {str(e)}"}), 500

    # Reddit search
    elif source == "reddit":
        # Documentation: https://github.com/pushshift/api
        pushshift_url = "https://api.pushshift.io/reddit/search/submission"
        params = {
            "q": query,
            "limit": 5,
            "sort": "desc",
            "sort_type": "created_utc"
        }
        try:
            rr = requests.get(pushshift_url, params=params)
            rr.raise_for_status()
            rr_data = rr.json()
            results = rr_data.get("data", [])
            if not results:
                return jsonify({"response": "No Reddit posts found."})

            # Extract titles and reddit links
            posts = []
            for post in results:
                title = post.get("title", "No title")
                permalink = post.get("full_link", "")
                posts.append({"title": title, "url": permalink})

            return jsonify({"response": f"Found {len(posts)} Reddit posts.", "reddit_posts": posts})
        except Exception as e:
            return jsonify({"error": f"Reddit search failed: {str(e)}"}), 500

    else:
        return jsonify({"error": "Invalid source"}), 400

@blueprint.route("/chat")
def chat():
    return render_template("aifypilot/chat.html",segment='chat')
