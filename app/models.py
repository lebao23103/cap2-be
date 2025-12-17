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
    updated_at = models.DateTimeField(auto_now=True)
    page_number = models.IntegerField(default=1)
    def __str__(self): return f"{self.user.username} read {self.book.title}"



# ==== Chat memory models ====
import uuid
from django.db import models
from django.contrib.auth.models import User

class ChatConversation(models.Model):
    """
    Mỗi cuộc trò chuyện của 1 user. Dùng UUID để FE lưu/khôi phục dễ.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_conversations")
    title = models.CharField(max_length=200, blank=True)
    role = models.CharField(max_length=100, default="helpful assistant")  # vai trò/“system prompt” của trợ lý
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "-updated_at"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        base = self.title or "Conversation"
        return f"{base} · {self.owner.username}"


class ChatMessage(models.Model):
    """
    Tin nhắn thuộc một cuộc trò chuyện.
    """
    ROLE_CHOICES = (("system", "system"), ("user", "user"), ("assistant", "assistant"))

    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="messages",
        db_index=True,
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()  # có thể để max_length nếu muốn giới hạn
    tokens = models.IntegerField(null=True, blank=True)  # tuỳ chọn: lưu token count để thống kê

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def __str__(self):
        return f"{self.role}: {self.content[:48]}"

# ================= BookNote Model =================
class BookNote(models.Model):
    """
    Model để user ghi chú (note/annotate) vào một đoạn text trong sách.
    Color được Frontend chọn, Backend lưu, Frontend lấy lại để render highlight.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='book_notes')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='notes')
    
    # Đoạn text được user chọn
    selected_text = models.TextField(help_text="Đoạn text được user chọn để ghi chú")
    
    # Nội dung note
    note_content = models.TextField(help_text="Ghi chú, cảm nhận của user")
    
    # Vị trí trong sách
    page_number = models.IntegerField(null=True, blank=True, help_text="Số trang")
    position_start = models.IntegerField(help_text="Vị trí bắt đầu")
    position_end = models.IntegerField(help_text="Vị trí kết thúc")
    
    # Màu highlight - Frontend chọn, Backend lưu, Frontend lấy lại render
    color = models.CharField(
        max_length=7,
        default='#FFEB3B',
        help_text="Hex color chosen by frontend (e.g., #FFEB3B)"
    )
    
    # Public/Private
    is_public = models.BooleanField(default=False)
    
    # Moderation Fields
    STATUS_CHOICES = (('visible', 'Visible'), ('hidden', 'Hidden'), ('deleted', 'Deleted'))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='visible')
    helpful_count = models.IntegerField(default=0)
    awful_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'book']),
            models.Index(fields=['book', 'is_public']),
            models.Index(fields=['page_number']),
            models.Index(fields=['status']), # Index for filtering visible notes
            models.Index(fields=['awful_count']), # Index for admin queue
        ]
        ordering = ['page_number', 'position_start']

    def __str__(self):
        return f"Note by {self.user.username} on {self.book.title}"


class NoteInteraction(models.Model):
    """
    Lưu trữ tương tác (vote) của user với note.
    Giúp đảm bảo mỗi user chỉ vote 1 lần và truy vết history.
    """
    INTERACTION_CHOICES = (('helpful', 'Helpful'), ('awful', 'Awful'))
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='note_interactions')
    note = models.ForeignKey(BookNote, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=10, choices=INTERACTION_CHOICES)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'note') # Mỗi user chỉ interact 1 lần với 1 note
        indexes = [
            models.Index(fields=['note', 'interaction_type']),
        ]

    def __str__(self):
        return f"{self.user.username} voted {self.interaction_type} on Note {self.note.id}"


class Question(models.Model):
    """
    Model để lưu trữ các câu hỏi trắc nghiệm cho sách
    """
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField(help_text="Nội dung câu hỏi")
    choice_a = models.TextField(help_text="Đáp án A")
    choice_b = models.TextField(help_text="Đáp án B")
    choice_c = models.TextField(help_text="Đáp án C")
    choice_d = models.TextField(help_text="Đáp án D")
    correct_answer = models.CharField(max_length=1, help_text="Đáp án đúng (A, B, C, D)")
    explanation = models.TextField(help_text="Giải thích/mô tả đáp án đúng", blank=True, null=True)
    order_num = models.IntegerField(help_text="Thứ tự câu hỏi trong sách/quiz")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ['order_num']
        indexes = [
            models.Index(fields=['book', 'order_num']),
        ]

    def __str__(self):
        return f"Question {self.order_num} for {self.book.title}"


class QuizSession(models.Model):
    """
    Model để lưu trữ phiên làm quiz của user
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_sessions')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='quiz_sessions')
    score = models.IntegerField(null=True, blank=True, help_text="Số câu đúng")
    total_questions = models.IntegerField(help_text="Tổng số câu hỏi")
    completed = models.BooleanField(default=False, help_text="Quiz đã hoàn thành chưa")
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'book']),
            models.Index(fields=['completed']),
        ]

    def __str__(self):
        status = "Completed" if self.completed else "In Progress"
        return f"Quiz Session for {self.book.title} - {status}"


class UserAnswer(models.Model):
    """
    Model để lưu trữ câu trả lời của user cho từng câu hỏi trong quiz
    """
    quiz_session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='user_answers')
    selected_answer = models.CharField(max_length=1, help_text="Đáp án user chọn (A, B, C, D)")
    is_correct = models.BooleanField(help_text="Đáp án đúng hay sai")
    
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['quiz_session', 'question']
        indexes = [
            models.Index(fields=['quiz_session']),
            models.Index(fields=['is_correct']),
        ]

    def __str__(self):
        return f"Answer for Question {self.question.id}: {self.selected_answer} ({'Correct' if self.is_correct else 'Incorrect'})"


class NoteComment(models.Model):
    """
    Hệ thống comment cho BookNote.
    Sử dụng chiến lược Soft Delete để giữ Audit Trail.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='note_comments')
    note = models.ForeignKey(BookNote, on_delete=models.CASCADE, related_name='comments')
    
    content = models.TextField()
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Soft Delete methodology
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='deleted_comments')

    class Meta:
        ordering = ['created_at'] # Cũ nhất lên đầu (như chat)
        indexes = [
            models.Index(fields=['note', 'is_deleted']), # Index để query comment active nhanh
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Comment by {self.user.username} on Note {self.note.id}"
