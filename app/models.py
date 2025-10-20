from django.db import models
from django.contrib.auth.models import User

class Book(models.Model):
    title = models.CharField(max_length=500)
    author = models.CharField(max_length=255, null=True, blank=True)
    pdf_file = models.FileField(upload_to="books/", null=True, blank=True)
    pages = models.IntegerField(null=True, blank=True)
    cover_image = models.ImageField(upload_to="book_covers/", null=True, blank=True)
    def __str__(self): return self.title


class UserBook(models.Model):
    # sách do user tự tạo/đăng
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_books")
    # (tuỳ) liên kết với Book chuẩn nếu là bản phái sinh
    original_book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True, related_name="variants")

    title = models.CharField(max_length=500)
    author = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    pdf_file = models.FileField(upload_to="user_books/", null=True, blank=True)
    pages = models.IntegerField(null=True, blank=True)
    cover_image = models.ImageField(upload_to="user_book_covers/", null=True, blank=True)

    is_approved = models.BooleanField(default=False)  # duyệt bởi admin trước khi public
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["is_approved"]),
        ]

    def __str__(self): return f"{self.title} (by {self.user.username})"


class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Review for {self.book.title} - Rating: {self.rating}"


class FavoriteBook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorite_books")
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    class Meta: unique_together = ('user', 'book')
    def __str__(self): return f'{self.user.username} - {self.book.title}'


class ReadingHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_history')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='history')
    read_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.user.username} read {self.book.title}"
