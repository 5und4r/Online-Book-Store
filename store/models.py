# store/models.py
from django.db import models
from django.contrib.auth.models import User

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    genre = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    cover_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.title

class UserBook(models.Model):
    # This defines our two allowed statuses
    STATUS_CHOICES = (
        ('saved', 'Saved'),
        ('purchased', 'Purchased'),
    )
    
    # The connections: Who is the user, and what is the book?
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    
    # The actual status of this relationship
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='saved')
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.status})"
    
# --- NEW HYBRID BACKUP MODEL ---
class GenreBackup(models.Model):
    # The name of the genre (e.g., 'Philosophy', 'Action')
    genre_name = models.CharField(max_length=50, unique=True)
    
    # We use a JSONField to store the entire list of 10 book dictionaries exactly as Google provided them!
    books_data = models.JSONField()
    
    # Keeps track of the last time Google successfully gave us fresh data
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.genre_name} Backup (Updated: {self.last_updated.strftime('%Y-%m-%d %H:%M')})"