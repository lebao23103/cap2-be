from rest_framework import serializers
from rest_framework.serializers import Serializer, CharField
from django.contrib.auth.models import User

from .models import (
    Book, Review, FavoriteBook, ReadingHistory, UserBook, BookNote, Question, QuizSession, UserAnswer
)
import re

# ===== Review =====
class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'book', 'user', 'rating', 'comment', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


# ===== Book =====
class BookSerializer(serializers.ModelSerializer):
    reviews = ReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    
    # Ép buộc trả về đường dẫn tương đối (Relative URL)
    pdf_file = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'author',
            'pdf_file',
            'pages',
            'cover_image',
            'reviews',
            'average_rating',
        ]
        
    def get_pdf_file(self, obj):
        if obj.pdf_file:
            return obj.pdf_file.url
        return None

    def get_cover_image(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
        return None

    def get_average_rating(self, obj):
        qs = obj.reviews.all()
        if not qs:
            return 0
        vals = [r.rating for r in qs if r.rating is not None]
        return round(sum(vals) / len(vals), 1) if vals else 0


# ===== UserBook (sách do user tạo) =====
class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class UserBookSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    pdf_file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = UserBook
        fields = [
            'id',
            'user',           # có thể set read_only=True nếu gán theo request.user trong view
            'original_book',
            'title',
            'author',
            'description',
            'pdf_file',
            'pages',
            'cover_image',
            'is_approved',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['is_approved', 'created_at', 'updated_at']

    def create(self, validated_data):
        # tự gán user hiện tại nếu có request
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data.setdefault('user', request.user)
        return super().create(validated_data)


# ===== FavoriteBook =====
class FavoriteBookBookMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'cover_image']

class FavoriteBookSerializer(serializers.ModelSerializer):
    book = FavoriteBookBookMiniSerializer(read_only=True)

    class Meta:
        model = FavoriteBook
        fields = ['id', 'book']


# ===== ReadingHistory =====
class ReadingHistorySerializer(serializers.ModelSerializer):
    book_id = serializers.IntegerField(source='book.id', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_author = serializers.CharField(source='book.author', read_only=True)
    book_cover = serializers.ImageField(source='book.cover_image', read_only=True)
    book_pages = serializers.IntegerField(source='book.pages', read_only=True)

    class Meta:
        model = ReadingHistory
        fields = ['id', 'book_id', 'book_title', 'book_author', 'book_cover', 'book_pages', 'read_at', 'updated_at', 'page_number']


# ===== Auth helper serializers (giữ nguyên) =====
class ResetPasswordSerializer(Serializer):
    email = CharField(required=True)
    confirmation_code = CharField(required=True)
    new_password = CharField(required=True)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

# ================= BookNote Serializer =================
class BookNoteSerializer(serializers.ModelSerializer):
    """
    Serializer đầy đủ cho CRUD operations.
    Include color field cho frontend nhớ user chọn màu nào.
    """
    user = serializers.StringRelatedField(read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)
    
    class Meta:
        model = BookNote
        fields = [
            'id',
            'user',
            'book',
            'book_title',
            'selected_text',
            'note_content',
            'page_number',
            'position_start',
            'position_end',
            'color',
            'is_public',
            'status',       # Moderator field
            'helpful_count', # Moderator field
            'awful_count',   # Moderator field
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['user', 'created_at', 'updated_at', 'helpful_count', 'awful_count', 'status']

    def validate_color(self, value):
        """Validate hex color format"""
        if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
            raise serializers.ValidationError(
                "Color must be in hex format (e.g., #FFEB3B, #4CAF50)"
            )
        return value.upper()

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class BookNoteListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer cho list view (GET /api/books/<id>/notes/)
    """
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = BookNote
        fields = [
            'id',
            'user_name',
            'selected_text',
            'note_content',
            'page_number',
            'color',
            'is_public',
            'helpful_count', # Public stats
            'awful_count',   # Public stats
            'created_at',
        ]

    def get_user_name(self, obj):
        """
        Privacy: Prefer First Name, otherwise mask the username/email.
        """
        user = obj.user
        fullname = f"{user.first_name} {user.last_name}".strip()
        if fullname:
            return fullname
            
        # Fallback to masked username if it looks like an email
        username = user.username
        if '@' in username:
            try:
                name_part = username.split('@')[0]
                if len(name_part) > 3:
                     return f"{name_part[:3]}***"
                return "User***"
            except:
                return "Anonymous"
        
        return username


# ================= Question Serializer =================
class QuestionSerializer(serializers.ModelSerializer):
    """
    Serializer cho model Question - dùng cho CRUD operations
    """
    class Meta:
        model = Question
        fields = [
            'id',
            'book',
            'question_text',
            'choice_a',
            'choice_b',
            'choice_c',
            'choice_d',
            'correct_answer',
            'explanation',
            'order_num',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class QuestionListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer cho list view
    """
    class Meta:
        model = Question
        fields = [
            'id',
            'question_text',
            'choice_a',
            'choice_b',
            'choice_c',
            'choice_d',
            'correct_answer',
            'explanation',
            'order_num',
        ]


# ================= Quiz Session Serializer =================
class UserAnswerSerializer(serializers.ModelSerializer):
    """
    Serializer cho câu trả lời của user
    """
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    correct_answer = serializers.CharField(source='question.correct_answer', read_only=True)
    
    class Meta:
        model = UserAnswer
        fields = [
            'id',
            'question',
            'question_text',
            'selected_answer',
            'correct_answer',
            'is_correct',
            'answered_at',
        ]


class QuizSessionSerializer(serializers.ModelSerializer):
    """
    Serializer cho phiên làm quiz
    """
    user_answers = UserAnswerSerializer(many=True, read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)
    
    class Meta:
        model = QuizSession
        fields = [
            'id',
            'user',
            'book',
            'book_title',
            'score',
            'total_questions',
            'completed',
            'started_at',
            'completed_at',
            'user_answers',
        ]


class QuizSessionListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer cho danh sách phiên làm quiz
    """
    book_title = serializers.CharField(source='book.title', read_only=True)
    
    class Meta:
        model = QuizSession
        fields = [
            'id',
            'book',
            'book_title',
            'score',
            'total_questions',
            'completed',
            'started_at',
            'completed_at',
        ]
