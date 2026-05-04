from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.http import JsonResponse
import random

# Cleaned up the imports to keep it neat!
from .models import Book, UserBook, GenreBackup
from .utils import (
    fetch_books_by_genre, 
    search_books, 
    chat_with_ai_librarian, 
    generate_blind_date_vibes, 
    generate_atmosphere
)


# =========================================================
# THE FIX: APP-WIDE PURCHASE RECOGNITION (SMART LOOP)
# =========================================================
def mark_owned_books(user, books_list):
    """Checks a list of API books against the user's purchased vault."""
    if not user.is_authenticated or not books_list:
        return books_list

    # Grab the titles and authors of everything this user has purchased
    owned_books = UserBook.objects.filter(
        user=user, 
        status='purchased'
    ).values_list('book__title', 'book__author')
    
    # Create a fast-lookup set (all lowercase to prevent mismatch errors)
    owned_set = set((t.lower().strip(), a.lower().strip()) for t, a in owned_books if t and a)

    # Loop through the API results and tag the ones they own!
    for book in books_list:
        book_title = book.get('title', '').lower().strip()
        book_author = book.get('author', '').lower().strip()
        
        if (book_title, book_author) in owned_set:
            book['is_owned'] = True
            
    return books_list

def home(request):
    genres = [
        {'name': 'Action', 'cover': 'https://picsum.photos/seed/actionbooks/400/600'},
        {'name': 'Comedy', 'cover': 'https://picsum.photos/seed/comedybooks/400/600'},
        {'name': 'Romance', 'cover': 'https://picsum.photos/seed/romancebooks/400/600'},
        {'name': 'Science Fiction', 'cover': 'https://picsum.photos/seed/scifibooks/400/600'},
        {'name': 'Philosophy', 'cover': 'https://picsum.photos/seed/philosophy/400/600'},
        {'name': 'Drama', 'cover': 'https://picsum.photos/seed/dramabooks/400/600'},
        {'name': 'History', 'cover': 'https://picsum.photos/seed/historybooks/400/600'},
        {'name': 'Fiction', 'cover': 'https://picsum.photos/seed/fictionbooks/400/600'},
        {'name': 'Humor', 'cover': 'https://picsum.photos/seed/humorbooks/400/600'},
        {'name': 'Mystery', 'cover': 'https://picsum.photos/seed/mysterybooks/400/600'},
        {'name': 'Fantasy', 'cover': 'https://picsum.photos/seed/fantasybooks/400/600'},
        {'name': 'Thriller', 'cover': 'https://picsum.photos/seed/thrillerbooks/400/600'},
        {'name': 'Biography', 'cover': 'https://picsum.photos/seed/biobooks/400/600'},
        {'name': 'Self-Help', 'cover': 'https://picsum.photos/seed/selfhelpbooks/400/600'},
        {'name': 'Horror', 'cover': 'https://picsum.photos/seed/horrorbooks/400/600'}
    ]

    selected_genre = request.GET.get('genre')
    selected_books = []
    random_books = []

    if selected_genre:
        # Check temporary cache first
        cache_key = f"hybrid_genre_{selected_genre.replace(' ', '_').lower()}"
        selected_books = cache.get(cache_key)
        if selected_books:
            print(f"⚡ Loaded {selected_genre} books instantly from Cache!")
        
        if not selected_books:
            print(f"Attempting to fetch fresh books for {selected_genre} from Google...")
            fresh_books = fetch_books_by_genre(selected_genre)
            
            if fresh_books:
                selected_books = fresh_books
                cache.set(cache_key, selected_books, 3600)
                GenreBackup.objects.update_or_create(
                    genre_name=selected_genre,
                    defaults={'books_data': fresh_books}
                )
            else:
                backup = GenreBackup.objects.filter(genre_name=selected_genre).first()
                if backup:
                    selected_books = backup.books_data
                    print(f"⚠️ Google API failed. Loaded {selected_genre} books from Backup!")
                    cache.set(cache_key, selected_books, 3600)
                
        # Apply the Smart Loop!
        selected_books = mark_owned_books(request.user, selected_books)
    else:
        # =========================================================
        # THE FIX: FRONT PAGE BESTSELLERS GENERATOR!
        # =========================================================
        cache_key = "front_page_bestsellers"
        random_books = cache.get(cache_key)
        if random_books:
            print("⚡ Loaded front page Bestsellers instantly from Cache!")
        
        if not random_books:
            print("Fetching universal Bestsellers for the front page...")
            
            # A curated seed list of absolute blockbuster hits
            famous_queries = [
                "intitle:Harry Potter", "intitle:Dune", "intitle:The Hobbit", 
                "intitle:Hunger Games", "intitle:Percy Jackson", "intitle:1984",
                "intitle:To Kill a Mockingbird", "intitle:The Alchemist",
                "intitle:Pride and Prejudice", "intitle:The Great Gatsby"
            ]
            
            random_books = []
            
            # Pick 4 random series from our hit list to keep the homepage fresh!
            selected_queries = random.sample(famous_queries, 4)
            
            for query in selected_queries:
                hits = search_books(query)
                if hits:
                    random_books.append(hits[0]) # Grab the top result
                    if len(hits) > 1:
                        random_books.append(hits[1]) # Grab the second result too
            
            if random_books:
                random.shuffle(random_books)
                cache.set(cache_key, random_books, 86400) # Cache for 24 hours!

        # Apply the Smart Loop to the bestsellers!
        random_books = mark_owned_books(request.user, random_books)

    context = {
        'genres': genres,
        'selected_genre': selected_genre,
        'selected_books': selected_books,
        'random_books': random_books  # Send the famous books to HTML!
    }
    return render(request, 'store/home.html', context)

def register_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to the Bookstore, {user.username}!")
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'store/register.html', {'form': form})

def login_user(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}.")
                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'store/login.html', {'form': form})

def logout_user(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('home')

# --- NEW VAULT LOGIC ---

@login_required(login_url='login')
def vault(request):
    # Fetch books from the database for the current logged-in user
    user_books = UserBook.objects.filter(user=request.user).order_by('-added_on')
    
    # Split them into Saved and Purchased
    saved_books = user_books.filter(status='saved')
    purchased_books = user_books.filter(status='purchased')
    
    context = {
        'saved_books': saved_books,
        'purchased_books': purchased_books
    }
    return render(request, 'store/vault.html', context)

@login_required(login_url='login')
def add_to_vault(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        author = request.POST.get('author')
        description = request.POST.get('description')
        cover_url = request.POST.get('cover_url')
        
        # WE ALSO CAPTURE PRICE AND RATING NOW SO IT SAVES IN CHECKOUT
        price = request.POST.get('price', 499)
        
        action = request.POST.get('action') # This will be 'saved' or 'purchased'
        
        # 1. Look for the book in our local DB, or create it if it's not there!
        book, created = Book.objects.get_or_create(
            title=title,
            author=author,
            defaults={'description': description, 'cover_url': cover_url, 'genre': 'General'}
        )
        
        # 2. TRAFFIC COP LOGIC:
        if action == 'purchased':
            request.session['pending_checkout_book_id'] = book.pk
            # Pass the generated Rupee price to the checkout page!
            request.session['pending_checkout_price'] = price
            return redirect('checkout')

        elif action == 'saved':
            user_book, created = UserBook.objects.get_or_create(
                user=request.user, book=book,
                defaults={'status': 'saved'}
            )
            if not created and user_book.status != 'saved':
                user_book.status = 'saved'
                user_book.save()
            messages.success(request, f"🔖 '{book.title}' has been saved to your wishlist!")
            return redirect(request.META.get('HTTP_REFERER', 'home'))

    return redirect('home')

def search(request):
    # Get the word the user typed in the search bar (the 'q' parameter)
    query = request.GET.get('q', '')
    books = []
    
    if query:
        cache_key = f"search_results_{query.replace(' ', '_').lower()}"
        books = cache.get(cache_key)
        if books:
            print(f"⚡ Loaded search results for '{query}' instantly from Cache!")
        
        if not books:
            print(f"Fetching search results for '{query}' from Google API...")
            books = search_books(query)
            if books: 
                cache.set(cache_key, books, 3600) 

        # Apply the Smart Loop here!
        books = mark_owned_books(request.user, books)

    context = {
        'books': books,
        'query': query,
    }
    return render(request, 'store/search.html', context)

def recommender(request):
    if 'chat_history' not in request.session:
        request.session['chat_history'] = [
            {'role': 'model', 'text': 'Hello! I am your AI Librarian. What kind of story are you in the mood for today?'}
        ]
        request.session['last_books'] = [] 
        request.session.modified = True

    if request.method == 'POST':
        if 'clear_chat' in request.POST:
            request.session['chat_history'] = [
                {'role': 'model', 'text': 'Hello! I am your AI Librarian. What kind of story are you in the mood for today?'}
            ]
            request.session['last_books'] = []
            request.session.modified = True
            return redirect('recommender')

        user_input = request.POST.get('user_input', '').strip()
        
        if user_input:
            chat_history = request.session['chat_history']
            chat_history.append({'role': 'user', 'text': user_input})
            
            print(f"🧠 Asking AI Librarian: {user_input}")
            ai_response = chat_with_ai_librarian(chat_history)
            
            chat_history.append({'role': 'model', 'text': ai_response['text']})
            request.session['chat_history'] = chat_history
            
            new_books = ai_response.get('books', [])
            if new_books:
                request.session['last_books'] = new_books
                
            request.session.modified = True
            
        return redirect('recommender')

    books_to_show = request.session.get('last_books', [])
    books_to_show = mark_owned_books(request.user, books_to_show)
    
    context = {
        'chat_history': request.session.get('chat_history', []),
        'books': books_to_show
    }
    return render(request, 'store/recommender.html', context)


def clear_chat(request):
    if 'chat_history' in request.session:
        del request.session['chat_history']
    return redirect('recommender')

@staff_member_required(login_url='login') 
def manager_dashboard(request):
    all_users = User.objects.prefetch_related('userbook_set__book').all().order_by('-date_joined')
    context = {'all_users': all_users}
    return render(request, 'store/manager_dashboard.html', context)

@login_required(login_url='login')
def checkout(request):
    book_id = request.session.get('pending_checkout_book_id')
    price = request.session.get('pending_checkout_price', 499) # Grab the dynamic price!
    
    if not book_id:
        messages.error(request, "Your cart is empty.")
        return redirect('home')
        
    book = Book.objects.get(id=book_id)

    if request.method == 'POST':
        user_book, created = UserBook.objects.get_or_create(
            user=request.user, book=book,
            defaults={'status': 'purchased'}
        )
        if not created:
            user_book.status = 'purchased'
            user_book.save()
            
        del request.session['pending_checkout_book_id']
        if 'pending_checkout_price' in request.session:
            del request.session['pending_checkout_price']
            
        messages.success(request, f"🎉 Payment Successful! '{book.title}' is now in your Vault.")
        return redirect('vault')

    # Pass the Rupee price to the checkout HTML
    return render(request, 'store/checkout.html', {'book': book, 'price': price})

@login_required(login_url='login')
def blind_date(request):
    backups = GenreBackup.objects.all()
    if not backups:
        messages.warning(request, "The bookstore is currently stocking the Blind Date shelves. Please click on some genres on the homepage first!")
        return redirect('home')
        
    backup = random.choice(backups)
    book = random.choice(backup.books_data)
    
    owned_check = UserBook.objects.filter(
        user=request.user, 
        book__title=book.get('title'), 
        book__author=book.get('author'), 
        status='purchased'
    ).exists()
    
    if owned_check:
        book['is_owned'] = True
    
    vibes = generate_blind_date_vibes(book)
    context = {'vibes': vibes, 'book': book }
    return render(request, 'store/blind_date.html', context)

def get_atmosphere(request):
    title = request.GET.get('title', 'Unknown Book')
    description = request.GET.get('description', '')
    
    cache_key = f"atmosphere_{title.replace(' ', '_').lower()}"
    atmosphere = cache.get(cache_key)
    
    if not atmosphere:
        print(f"✨ Generating fresh AI Atmosphere for '{title}'...")
        atmosphere = generate_atmosphere(title, description)
        cache.set(cache_key, atmosphere, 86400)
    else:
        print(f"⚡ Loaded Atmosphere for '{title}' instantly from Cache!")
        
    return JsonResponse(atmosphere)