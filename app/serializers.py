from rest_framework import serializers
from rest_framework.serializers import Serializer, CharField

from .models import (
    Book, Review, FavoriteBook, ReadingHistory, UserBook,BookNote
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
    # DRF tự xử lý FileField -> URL nếu dùng DefaultStorage
    pdf_file = serializers.FileField(required=False, allow_null=True)

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

    def get_average_rating(self, obj):
        qs = obj.reviews.all()
        if not qs:
            return 0
        vals = [r.rating for r in qs if r.rating is not None]
        return round(sum(vals) / len(vals), 1) if vals else 0


# ===== UserBook (sách do user tạo) =====
class UserBookSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = ReadingHistory
        fields = ['id', 'book_id', 'book_title', 'book_author', 'book_cover', 'read_at']


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
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

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
    user_name = serializers.CharField(source='user.username', read_only=True)
    
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
            'created_at',
        ]