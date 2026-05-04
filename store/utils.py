"""
Utility functions for the Online Book Store Django app.
This module handles book fetching from external APIs (Google Books, Open Library),
AI-powered features using Gemini, and various book-related utilities.
"""

import requests
import json
import time
import random
from django.conf import settings
from google import genai
from google.genai import types

def fetch_books_by_genre(genre):
    """
    Fetches books from Google Books API based on a specific genre.
    Includes retry logic for API rate limits and processes book data
    including ratings and price calculations in INR.
    
    Args:
        genre (str): The book genre to search for.
    
    Returns:
        list: List of dictionaries containing book information.
    """
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {'q': genre, 'maxResults': 10, 'key': settings.GOOGLE_BOOKS_API_KEY}
    delays = [1, 2, 4]
    for attempt in range(4):
        # Retry loop to handle API rate limits and network errors
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                books = []
                for item in items:
                    volume_info = item.get('volumeInfo', {})
                    pub_date = str(volume_info.get('publishedDate', ''))
                    year = pub_date[:4] if pub_date else 'Unknown'
                    
                    read_url = volume_info.get('webReaderLink')
                    if not read_url:
                        read_url = volume_info.get('previewLink', '#')

                    # ==========================================
                    # NEW: GET RATING & CALCULATE RUPEE PRICE
                    # ==========================================
                    rating = volume_info.get('averageRating')
                    if not rating:
                        # Deterministic fake rating (so it doesn't change on refresh)
                        rating = round(3.8 + (len(volume_info.get('title', 'A')) % 12) / 10, 1)

                    price = 0
                    sale_info = item.get('saleInfo', {})
                    if sale_info.get('saleability') == 'FOR_SALE' and 'retailPrice' in sale_info:
                        amount = sale_info['retailPrice'].get('amount', 0)
                        currency = sale_info['retailPrice'].get('currencyCode', '')
                        if currency == 'USD':
                            price = int(amount * 83) # USD to INR
                        elif currency == 'INR':
                            price = int(amount)
                            
                    if price == 0:
                        # Smart Fallback: Calculate INR price based on page count
                        pages = volume_info.get('pageCount', 300)
                        if pages == 0: pages = 250 + (len(volume_info.get('title', 'A')) * 5)
                        price = int(150 + (pages * 1.2))

                    book_data = {
                        'id': item.get('id'),
                        'title': volume_info.get('title', 'Unknown Title'),
                        'author': ", ".join(volume_info.get('authors', ['Unknown Author'])),
                        'description': volume_info.get('description', 'No description available.'),
                        'cover_url': volume_info.get('imageLinks', {}).get('thumbnail', '').replace('http:', 'https:'),
                        'genre': genre,
                        'year': year,
                        'pages': volume_info.get('pageCount', 0),
                        'read_url': read_url,
                        'rating': rating,   # <-- INJECTED INTO DICTIONARY
                        'price': price      # <-- INJECTED INTO DICTIONARY
                    }
                    books.append(book_data)
                return books
            elif response.status_code in [429, 403]: 
                if attempt < 3:
                    time.sleep(delays[attempt])
                    continue
        except requests.exceptions.RequestException:
            if attempt < 3:
                time.sleep(delays[attempt])
                continue
    return []

def search_books(query):
    google_url = "https://www.googleapis.com/books/v1/volumes"
    google_params = {'q': query, 'maxResults': 20, 'key': settings.GOOGLE_BOOKS_API_KEY}
    try:
        response = requests.get(google_url, params=google_params, timeout=3)
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            books = []
            for item in items:
                volume_info = item.get('volumeInfo', {})
                pub_date = str(volume_info.get('publishedDate', ''))
                year = pub_date[:4] if pub_date else 'Unknown'
                pages = volume_info.get('pageCount', 0)
                
                read_url = volume_info.get('webReaderLink')
                if not read_url:
                    read_url = volume_info.get('previewLink', '#')

                # ==========================================
                # NEW: GET RATING & CALCULATE RUPEE PRICE
                # ==========================================
                rating = volume_info.get('averageRating')
                if not rating:
                    rating = round(3.8 + (len(volume_info.get('title', 'A')) % 12) / 10, 1)

                price = 0
                sale_info = item.get('saleInfo', {})
                if sale_info.get('saleability') == 'FOR_SALE' and 'retailPrice' in sale_info:
                    amount = sale_info['retailPrice'].get('amount', 0)
                    currency = sale_info['retailPrice'].get('currencyCode', '')
                    if currency == 'USD':
                        price = int(amount * 83)
                    elif currency == 'INR':
                        price = int(amount)
                        
                if price == 0:
                    pgs = pages if pages > 0 else 250 + (len(volume_info.get('title', 'A')) * 5)
                    price = int(150 + (pgs * 1.2))

                book_data = {
                    'id': item.get('id', 'unknown'),
                    'title': volume_info.get('title', 'Unknown Title'),
                    'author': ", ".join(volume_info.get('authors', ['Unknown Author'])),
                    'description': volume_info.get('description', 'No description available.'),
                    'cover_url': volume_info.get('imageLinks', {}).get('thumbnail', '').replace('http:', 'https:'),
                    'genre': 'Search Result',
                    'year': year,
                    'pages': pages,
                    'read_url': read_url,
                    'rating': rating,
                    'price': price
                }
                books.append(book_data)
            if books:
                return books
    except requests.exceptions.RequestException:
        pass

    # ENGINE 2: OPEN LIBRARY
    print(f"⚠️ Google Books API failed or empty. Falling back to Open Library for '{query}'...")
    ol_url = "https://openlibrary.org/search.json"
    ol_params = {'q': query, 'limit': 20}
    headers = {'User-Agent': 'AIBookstoreApp/1.0'}
    
    try:
        ol_res = requests.get(ol_url, params=ol_params, headers=headers, timeout=5)
        if ol_res.status_code == 200:
            docs = ol_res.json().get('docs', [])
            books = []
            for doc in docs:
                authors = doc.get('author_name')
                author_string = ", ".join(authors) if isinstance(authors, list) else 'Unknown Author'
                cover_id = doc.get('cover_i')
                cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else ''
                book_key = doc.get('key', 'unknown').replace('/works/', '')
                read_url = f"https://openlibrary.org/works/{book_key}" 
                
                # Rating and Price for Open Library
                pages = doc.get('number_of_pages_median', 0)
                rating = round(3.5 + (len(str(doc.get('title', 'A'))) % 15) / 10, 1)
                pgs = pages if pages > 0 else 300
                price = int(150 + (pgs * 1.2))
                
                book_data = {
                    'id': book_key,
                    'title': str(doc.get('title', 'Unknown Title')),
                    'author': author_string,
                    'description': 'Synopsis currently unavailable from open-source database.',
                    'cover_url': cover_url,
                    'genre': 'Search Result',
                    'year': str(doc.get('first_publish_year', 'Unknown')),
                    'pages': pages,
                    'read_url': read_url,
                    'rating': rating,
                    'price': price
                }
                books.append(book_data)
            if books:
                return books
    except Exception:
        pass
    return []

def generate_atmosphere(title, description):
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = f"""
    You are a creative book aesthetic generator.
    Based on the book '{title}', generate a reading atmosphere.
    Description: {description}
    Return ONLY a valid JSON object with EXACTLY these 3 keys. Keep them short and punchy.
    "soundtrack": "A short sentence recommending music or ambient sounds.",
    "snack": "A short sentence recommending a specific snack or drink pairing.",
    "setting": "A short sentence describing the perfect physical location/lighting to read this."
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        text_content = response.text or "{}"
        text_content = text_content.replace('```json', '').replace('```', '').strip()
        data = json.loads(text_content)
        if "soundtrack" in data and "snack" in data and "setting" in data:
            return data
    except Exception as e:
        print(f"⚠️ Atmosphere Error for {title}: {e}")
        pass
    return {
        "soundtrack": "Epic cinematic orchestral score.",
        "snack": "A hot cup of coffee and your favorite comfort food.",
        "setting": "A cozy armchair with a warm reading lamp."
    }

def chat_with_ai_librarian(chat_history):
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    system_instruction = """
    You are an expert, friendly AI librarian.
    Chat with the user naturally about books, authors, and genres.
    If the user asks for recommendations, provide exactly 10 book titles.
    Always return your response as a JSON object with two keys:
    "message": Your conversational text reply to the user.
    "books": A list of book titles (strings). Leave empty [] if you are just chatting and not recommending anything.
    """
    contents = []
    for msg in chat_history:
        role = 'user' if msg['role'] == 'user' else 'model'
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg['text'])]))
        
    delays = [1, 2, 4, 8, 16]
    response = None
    
    for attempt in range(6): 
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=system_instruction, response_mime_type="application/json")
            )
            break 
        except Exception:
            if attempt < 5:
                time.sleep(delays[attempt])
                
    if response is None:
        return {"text": "I'm currently assisting too many readers! Please give me a moment and try again.", "books": []}
            
    text_content = response.text or "{}"
    try:
        response_data = json.loads(text_content)
    except json.JSONDecodeError:
        response_data = {"message": "I got a bit confused, let's try that again.", "books": []}
        
    ai_message = response_data.get("message", "Here are some thoughts.")
    book_titles = response_data.get("books", [])[:10]
    
    recommended_books = []
    if book_titles:
        for title in book_titles:
            time.sleep(0.2) 
            book_data = {
                'id': f"ai-pick-{title.replace(' ', '-').lower()}",
                'title': title,
                'author': 'Unknown Author',
                'description': 'The AI Librarian highly recommends this title!',
                'cover_url': '',
                'genre': 'AI Pick',
                'year': 'Unknown',
                'pages': 0,
                'read_url': f"https://www.google.com/search?tbm=bks&q={title.replace(' ', '+')}",
                'rating': round(random.uniform(4.2, 4.9), 1), # AI picks always have great ratings!
                'price': random.randint(399, 899)
            }
            google_url = "https://www.googleapis.com/books/v1/volumes"
            google_params = {'q': f"intitle:{title}", 'maxResults': 1, 'key': settings.GOOGLE_BOOKS_API_KEY}
            try:
                res = requests.get(google_url, params=google_params, timeout=2)
                if res.status_code == 200:
                    items = res.json().get('items', [])
                    if items:
                        item = items[0]
                        volume_info = item.get('volumeInfo', {})
                        pub_date = str(volume_info.get('publishedDate', ''))
                        
                        read_url = volume_info.get('webReaderLink')
                        if not read_url:
                            read_url = volume_info.get('previewLink', book_data['read_url'])
                            
                        # Rating & Price parsing for AI Picks
                        rating = volume_info.get('averageRating', book_data['rating'])
                        pages = volume_info.get('pageCount', 0)
                        
                        price = 0
                        sale_info = item.get('saleInfo', {})
                        if sale_info.get('saleability') == 'FOR_SALE' and 'retailPrice' in sale_info:
                            amt = sale_info['retailPrice'].get('amount', 0)
                            cur = sale_info['retailPrice'].get('currencyCode', '')
                            if cur == 'USD': price = int(amt * 83)
                            elif cur == 'INR': price = int(amt)
                        
                        if price == 0:
                            pgs = pages if pages > 0 else 300
                            price = int(150 + (pgs * 1.2))

                        book_data['id'] = item.get('id', book_data['id'])
                        book_data['title'] = volume_info.get('title', title)
                        book_data['author'] = ", ".join(volume_info.get('authors', ['Unknown Author']))
                        book_data['description'] = volume_info.get('description', book_data['description'])
                        book_data['cover_url'] = volume_info.get('imageLinks', {}).get('thumbnail', '').replace('http:', 'https:')
                        book_data['year'] = pub_date[:4] if pub_date else 'Unknown'
                        book_data['pages'] = pages
                        book_data['read_url'] = read_url
                        book_data['rating'] = rating
                        book_data['price'] = price
                        
            except requests.exceptions.RequestException:
                pass 
            recommended_books.append(book_data) 
                
    return {"text": ai_message, "books": recommended_books}

def generate_blind_date_vibes(book):
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    # We secretly extract the title and author to give Gemini context!
    title = book.get('title', 'Unknown Title')
    author = book.get('author', 'Unknown Author')
    description = book.get('description', '')
    
    prompt = f"""
    You are creating a 'Blind Date with a Book' mystery wrapper.
    Generate exactly 3 short, intriguing bullet points (vibes) for this book.
    If the description is empty, use your vast AI knowledge of the book based on the Title and Author.
    
    CRITICAL RULES:
    1. Do NOT reveal the book's title ({title}) or author ({author}) in your response.
    2. Format strictly as a JSON array of 3 strings. Example: ["Vibe 1", "Vibe 2", "Vibe 3"]
    
    Title: {title}
    Author: {author}
    Description: {description}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        # Clean up the response to ensure perfect JSON
        text_content = response.text or "[]"
        text_content = text_content.replace('```json', '').replace('```', '').strip()
        
        vibes = json.loads(text_content)
        
        if isinstance(vibes, list) and len(vibes) >= 3:
            return vibes[:3]
    except Exception as e:
        print(f"⚠️ Gemini Vibe Error: {e}")
        pass
        
    # The ultimate fallback just in case!
    return [
        "🗡️ A protagonist pushed to their absolute limits", 
        "🌑 A world filled with secrets waiting to be uncovered", 
        "🤯 A journey that will keep you guessing until the end"
    ]