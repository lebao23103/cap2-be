from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import Avg, Q, Count
from django.core.mail import send_mail
from django.core.cache import cache
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDate
from django.shortcuts import render, get_object_or_404
from rest_framework import status, permissions, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Book, FavoriteBook, ReadingHistory, UserBook, Review, Question, QuizSession, UserAnswer, BookNote, NoteInteraction
from .serializers import (
    BookSerializer, ReviewSerializer, FavoriteBookSerializer,
    ReadingHistorySerializer, ResetPasswordSerializer, ChangePasswordSerializer,
    UserBookSerializer, QuestionSerializer, QuestionListSerializer,
    QuizSessionSerializer, QuizSessionListSerializer, UserAnswerSerializer
)

import random, string
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
def home(request):
    return HttpResponse("Bookquest")

# ================= AUTH (Giữ nguyên) =================
class RegisterView(APIView):
    def post(self, request):
        data = request.data
        username = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        if password != confirm_password:
            return Response({'error': 'Passwords do not match!'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=username).exists():
            return Response({'error': 'Email already exists!'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate username from Name
        base_name = f"{first_name}{last_name}".lower().replace(" ", "")
        # Fallback to email prefix if no name provided
        if not base_name:
            base_name = username.split('@')[0]
            
        # Ensure alphanumeric-ish
        import re
        base_name = re.sub(r'[^a-z0-9]', '', base_name) or 'user'

        final_username = base_name
        counter = 1
        while User.objects.filter(username=final_username).exists():
            final_username = f"{base_name}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=final_username, email=username, password=password,
            first_name=first_name, last_name=last_name
        )
        return Response({'message': 'User registered successfully!'}, status=status.HTTP_201_CREATED)

from django.contrib.auth.models import update_last_login

class LoginView(APIView):
    def post(self, request):
        data = request.data
        email = data.get('email'); password = data.get('password')
        try:
            user = User.objects.get(email=email)
            auth_user = authenticate(request, username=user.username, password=password)
            if auth_user is None:
                return Response({'message': 'Invalid password!'}, status=status.HTTP_401_UNAUTHORIZED)

            # Cập nhật last_login để không bị "Never seen"
            update_last_login(None, auth_user)

            refresh = RefreshToken.for_user(auth_user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),   # <--- thêm dòng này
                'user': {
                    'id': auth_user.id,
                    'first_name': auth_user.first_name,
                    'last_name': auth_user.last_name,
                    'email': auth_user.email,
                    'is_superuser': auth_user.is_superuser,
                }
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'message': 'User with this email does not exist!'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logged out successfully"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ForgotPasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User with this email does not exist!'}, status=status.HTTP_404_NOT_FOUND)
        code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        cache.set(f"password_reset_code_{email}", code, timeout=600)
        try:
            send_mail(
                subject="Confirmation Code - Bookquest",
                message=f"Hello {user.first_name},\n\nYour confirmation code is: {code}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )
            return Response({'message': 'Confirmation code sent to your email!'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Failed to send email.', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ResetPasswordView(APIView):
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        email = serializer.validated_data['email']
        confirmation_code = serializer.validated_data['confirmation_code']
        new_password = serializer.validated_data['new_password']
        cached_code = cache.get(f"password_reset_code_{email}")
        if not cached_code or cached_code != confirmation_code:
            return Response({'error': 'Invalid or expired confirmation code!'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User with this email does not exist!'}, status=status.HTTP_404_NOT_FOUND)
        user.set_password(new_password); user.save()
        cache.delete(f"password_reset_code_{email}")
        return Response({'message': 'Password has been reset successfully!'}, status=status.HTTP_200_OK)

def is_admin(user): return user.is_authenticated and user.is_superuser

@permission_classes([IsAuthenticated])
@api_view(['GET'])
def admin_dashboard(request):
    if is_admin(request.user):
        return Response({'message': 'Welcome Admin!'}, status=status.HTTP_200_OK)
    return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

# ================= BOOK APIs =================
@api_view(['GET'])
def search_books(request):
    q = request.query_params.get('q', '').strip()
    if not q:
        return Response({'error': 'Query parameter "q" is required.'}, status=400)
    books = Book.objects.filter(Q(title__icontains=q) | Q(author__icontains=q))
    if not books.exists():
        return Response({'message': 'No books found matching your query.'}, status=404)
    return Response(BookSerializer(books, many=True).data, status=200)

@api_view(['GET'])
def all_books(request):
    return Response(BookSerializer(Book.objects.all(), many=True).data)

@api_view(['GET'])
def book_detail_view(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    avg = book.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    data = BookSerializer(book).data
    data['average_rating'] = round(avg, 1)
    return Response(data)

@api_view(['GET'])
def books_by_author(request, author_name):
    books = Book.objects.filter(author__icontains=author_name)
    return Response(BookSerializer(books, many=True).data)

@api_view(['GET'])
def book_content_by_id(request, book_id):
    """Trả URL file PDF (local)."""
    book = get_object_or_404(Book, id=book_id)
    if not book.pdf_file:
        return Response({'error': 'No PDF available for this book.'}, status=404)
    return Response({
        'title': book.title,
        'author': book.author,
        # Trả về đường dẫn tương đối (ví dụ: /media/books/file.pdf)
        # Frontend sẽ tự động nối với domain hiện tại
        'pdf_url': book.pdf_file.url,
    })

# ================= REVIEW =================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_review(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    data = dict(request.data); data['book'] = book.id
    s = ReviewSerializer(data=data, context={'request': request})
    if s.is_valid():
        s.save(user=request.user, book=book)
        return Response(s.data, status=201)
    return Response(s.errors, status=400)

@api_view(['GET'])
def get_book_reviews(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    return Response(ReviewSerializer(book.reviews.all(), many=True).data)

# ================= PROFILE =================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request, user_id):
    if request.user.id != int(user_id):
        return Response({"error": "You can only view your own profile."}, status=status.HTTP_403_FORBIDDEN)
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response({"first_name": user.first_name, "last_name": user.last_name, "email": user.email}, status=200)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_profile(request, user_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        return Response({"error": "User not found"}, status=404)
    data = request.data
    user.first_name = data.get('first_name', user.first_name)
    user.last_name  = data.get('last_name',  user.last_name)
    user.email      = data.get('email',      user.email)
    if 'password' in data: user.set_password(data['password'])
    user.save()
    return Response({"first_name": user.first_name, "last_name": user.last_name, "email": user.email}, status=200)

class ChangePasswordView(views.APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request):
        user = request.user
        s = ChangePasswordSerializer(data=request.data)
        if s.is_valid():
            if not user.check_password(s.validated_data["old_password"]):
                return Response({"error": "Old password is incorrect."}, status=400)
            if s.validated_data["new_password"] != s.validated_data["confirm_password"]:
                return Response({"error": "Passwords do not match."}, status=400)
            user.set_password(s.validated_data["new_password"]); user.save()
            return Response({"success": "Password changed successfully."}, status=200)
        return Response(s.errors, status=400)

# ================= FAVORITES =================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_favorites(request):
    book_id = request.data.get('book_id')
    if not book_id: return Response({"error": "Book ID is required"}, status=400)
    try: book = Book.objects.get(id=book_id)
    except Book.DoesNotExist: return Response({"error": "Book not found"}, status=404)
    if FavoriteBook.objects.filter(user=request.user, book=book).exists():
        return Response({"message": "Book already added to favorites!"}, status=200)
    FavoriteBook.objects.create(user=request.user, book=book)
    return Response({"message": "Book added to favorites!"}, status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_favorites(request):
    favorites = FavoriteBook.objects.filter(user=request.user)
    books = [f.book for f in favorites]
    return Response(BookSerializer(books, many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_from_favorites(request):
    book_id = request.data.get('book_id')
    if not book_id: return Response({"error": "Book ID is required"}, status=400)
    try: book = Book.objects.get(id=book_id)
    except Book.DoesNotExist: return Response({"error": "Book not found"}, status=404)
    fav = FavoriteBook.objects.filter(user=request.user, book=book).first()
    if not fav: return Response({"message": "Book is not in favorites."}, status=400)
    fav.delete(); return Response({"message": "Book removed from favorites!"}, status=200)

# ================= READING HISTORY =================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_reading_history(request):
    book_id = request.data.get('book_id')
    if not book_id: return Response({"error": "Book ID is required"}, status=400)
    try: book = Book.objects.get(id=book_id)
    except Book.DoesNotExist: return Response({"error": "Book not found"}, status=404)
    ReadingHistory.objects.get_or_create(user=request.user, book=book)
    return Response({"message": "Book added to reading history"}, status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_reading_history(request):
    history = ReadingHistory.objects.filter(user=request.user).order_by('-updated_at')
    return Response(ReadingHistorySerializer(history, many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_reading_progress(request, book_id):
    """
    Cập nhật page_number cho sách trong ReadingHistory.
    Nếu chưa có, tạo mới.
    """
    page = request.data.get('page_number', 1)
    book = get_object_or_404(Book, id=book_id)
    
    # Tìm lịch sử gần nhất hoặc tạo mới
    history, created = ReadingHistory.objects.get_or_create(
        user=request.user, 
        book=book,
        defaults={'page_number': page}
    )
    
    if not created:
        history.page_number = page
        history.save() # Auto updates updated_at
        
    return Response({'message': 'Progress updated', 'page_number': history.page_number}, status=200)

# ================= ADMIN LISTS =================
@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_users(request):
    users = User.objects.all()
    # Explicitly return fields for UI: Username, Name, Email, Status, Last Login
    data = []
    for u in users:
        data.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'is_staff': u.is_staff,
            'is_superuser': u.is_superuser,
            'is_active': u.is_active,
            'last_login': u.last_login,
            'is_online': bool(cache.get(f'seen_{u.id}'))
        })
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_books(request):
    books = Book.objects.all()
    data = [{
        'id': b.id, 'title': b.title, 'author': b.author,
        'pdf_url': (b.pdf_file.url if b.pdf_file else None),
        'pages': b.pages,
        'cover_image': (b.cover_image.url if b.cover_image else None),
    } for b in books]
    return Response(data)
# --- STATS: users ---
@api_view(['GET'])
def rating_statistics(request):
    """
    Trả:
      - rates: {rating_value: count}
      - average_rating: trung bình cộng (2 chữ số)
    """
    counts = Review.objects.values('rating').annotate(count=Count('id')).order_by('rating')
    rates = {row['rating']: row['count'] for row in counts if row['rating'] is not None}
    total = sum(rates.values())
    avg = round(sum((k or 0) * v for k, v in rates.items()) / total, 2) if total else 0
    return Response({"rates": rates, "average_rating": avg})
@api_view(['GET'])
# @permission_classes([IsAdminUser])  # Bật nếu muốn chỉ admin xem
def report_statistics(request):
    # Basic Counts
    total_books = Book.objects.count()
    total_reads = ReadingHistory.objects.count()
    total_users = User.objects.count()

    # Most Read Book
    most = (
        ReadingHistory.objects
        .values('book')
        .annotate(read_count=Count('id'))
        .order_by('-read_count')
        .first()
    )
    most_read_book = None
    if most and most['book']:
        try:
            b = Book.objects.get(id=most['book'])
            most_read_book = {
                "id": b.id,
                "title": b.title,
                "author": b.author,
                "read_count": most['read_count'],
            }
        except Book.DoesNotExist:
            most_read_book = None

    # Reviews & Ratings
    stats = Review.objects.aggregate(total=Count('id'), avg=Avg('rating'))
    average_rating = round(stats['avg'] or 0, 2)

    # 1. Rating Distribution for Bar Chart
    # Returns list like: [{'rating': 5, 'count': 10}, {'rating': 4, 'count': 5}, ...]
    rating_dist_query = (
        Review.objects
        .values('rating')
        .annotate(count=Count('id'))
        .order_by('rating')
    )
    # Convert to standard dictionary {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    rating_distribution = {i: 0 for i in range(1, 6)}
    for r in rating_dist_query:
        rating_distribution[r['rating']] = r['count']

    # 2. User Roles for Pie Chart
    # Standard query counting staff vs non-staff
    staff_count = User.objects.filter(is_staff=True).count()
    user_count = total_users - staff_count
    user_roles = {
        "admin": staff_count,
        "user": user_count
    }

    return Response({
        "total_books": total_books,
        "total_reads": total_reads,
        "most_read_book": most_read_book,
        "total_users": total_users,
        "total_reviews": stats['total'] or 0,
        "average_rating": average_rating,
        "rating_distribution": rating_distribution,
        "user_roles": user_roles
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])  # Chỉ admin truy cập (đổi nếu muốn public)
def user_roles_statistics(request):
    return Response({
        "active_users": User.objects.filter(is_active=True).count(),
        "total_users": User.objects.count(),
    })

# --- STATS: books ---
from .models import Book

@api_view(['GET'])
@permission_classes([IsAdminUser])  # Chỉ admin (đổi nếu muốn public)
def total_books(request):
    return Response({"total_books": Book.objects.count()})

# ================= USERBOOK (tạo/duyệt) =================
class CreateUserBookView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        title = request.data.get('title')
        description = request.data.get('description')
        pdf_file = request.FILES.get('pdf_file')
        cover_image = request.FILES.get('cover_image')
        if not title or not pdf_file:
            return Response({'error': 'title and pdf_file are required.'}, status=400)
        author_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
        user_book = UserBook.objects.create(
            user=request.user, title=title, author=author_name,
            description=description, pdf_file=pdf_file, cover_image=cover_image,
            is_approved=False
        )
        return Response({'message': 'Book created successfully and awaits admin approval!',
                         'book_id': user_book.id}, status=201)

class ListUserBooksView(APIView):
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    def get(self, request):
        books = UserBook.objects.filter(is_approved=False)
        return Response(UserBookSerializer(books, many=True).data)

class ListApprovedBooksView(APIView):
    def get(self, request):
        approved = UserBook.objects.filter(is_approved=True)
        return Response(UserBookSerializer(approved, many=True).data)

class RejectAndDeleteBookView(APIView):
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    def delete(self, request, book_id, *args, **kwargs):
        user_book = get_object_or_404(UserBook, id=book_id)
        if not user_book.is_approved:
            user_book.delete()
            return Response({"message": f"The book '{user_book.title}' has been rejected and deleted."}, status=200)
        return Response({"error": "Only unapproved books can be rejected and deleted."}, status=400)

class ApproveUserBookView(APIView):
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    def put(self, request, user_book_id):
        try:
            ub = UserBook.objects.get(id=user_book_id)
        except UserBook.DoesNotExist:
            return Response({"message": "User book not found."}, status=404)
        ub.is_approved = True
        ub.save(update_fields=['is_approved'])
        b = Book.objects.create(
            title=ub.title, author=ub.author, pages=ub.pages,
            cover_image=ub.cover_image if ub.cover_image else None,
        )
        if ub.pdf_file:
            b.pdf_file = ub.pdf_file
            b.save(update_fields=['pdf_file'])
        return Response({"message": "Book approved and published.", "book_id": b.id}, status=200)

# ================= CRUD users =================

@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_user(request):
    data = request.data
    if 'username' not in data or 'email' not in data or 'password' not in data:
        return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=data['username']).exists():
        return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        username=data['username'],
        email=data['email'],
        password=data['password']
    )
    return Response({"id": user.id, "username": user.username, "email": user.email},
                    status=status.HTTP_201_CREATED)

# Hardcoded Root Admins (Trusted List) - moved to Backend for security
ROOT_ADMINS = ['tranbach@gmail.com', 'giabao']

@api_view(['PUT'])
@permission_classes([IsAdminUser])
def update_user(request, user_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    # SECURITY CHECKS
    # 1. Protect Root Admins from being modified by ANYONE via API
    if user.username in ROOT_ADMINS or user.email in ROOT_ADMINS:
        return Response({"error": "Permission Denied: Cannot modify a Root Admin."}, status=status.HTTP_403_FORBIDDEN)

    # 2. Hierarchy: If target is Superuser, only Root Admin can modify them
    if user.is_superuser:
         # Check if requester is Root
         requester_email = request.user.email
         requester_username = request.user.username
         if requester_email not in ROOT_ADMINS and requester_username not in ROOT_ADMINS:
             return Response({"error": "Permission Denied: Only Root Admins can modify other Superusers."}, status=status.HTTP_403_FORBIDDEN)

    data = request.data
    user.username = data.get('username', user.username)
    user.email = data.get('email', user.email)
    if 'is_staff' in data:
        user.is_staff = data['is_staff']
    if 'password' in data and data['password']:
        user.set_password(data['password'])
    user.save()

    return Response({"id": user.id, "username": user.username, "email": user.email, "is_staff": user.is_staff},
                    status=status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_user(request, user_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    # SECURITY CHECKS
    # 1. Protect Root Admins
    if user.username in ROOT_ADMINS or user.email in ROOT_ADMINS:
        return Response({"error": "Permission Denied: Cannot delete a Root Admin."}, status=status.HTTP_403_FORBIDDEN)
    
    # 2. Protect Superusers
    if user.is_superuser:
         requester_email = request.user.email
         requester_username = request.user.username
         if requester_email not in ROOT_ADMINS and requester_username not in ROOT_ADMINS:
             return Response({"error": "Permission Denied: Only Root Admins can delete Superusers."}, status=status.HTTP_403_FORBIDDEN)

    user.delete()
    return Response({"message": "User deleted successfully"}, status=status.HTTP_200_OK)

# ================= CRUD books =================
@api_view(['PUT'])  # hoặc ['PATCH'] nếu muốn cập nhật từng phần
@permission_classes([IsAdminUser])
def edit_book_fields(request, pk):
    """
    Cập nhật các trường hợp lệ của Book theo schema mới:
    - title, author, pages (trong request.data)
    - cover_image, pdf_file (trong request.FILES)
    """
    book = get_object_or_404(Book, pk=pk)

    # Trường text/number
    for field in ['title', 'author', 'pages']:
        if field in request.data:
            setattr(book, field, request.data.get(field))

    # Trường file
    if 'cover_image' in request.FILES:
        book.cover_image = request.FILES['cover_image']
    if 'pdf_file' in request.FILES:
        book.pdf_file = request.FILES['pdf_file']

    try:
        book.save()
    except Exception as e:
        return Response({"error": f"Failed to update book: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(BookSerializer(book).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_book(request):
    """
    Tạo mới một cuốn sách (Admin only)
    """
    try:
        title = request.data.get('title')
        if not title:
            return Response({"error": "Title is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        book = Book.objects.create(
            title=title,
            author=request.data.get('author'),
            pages=request.data.get('pages'),
            pdf_file=request.FILES.get('pdf_file'),
            cover_image=request.FILES.get('cover_image')
        )
        return Response(BookSerializer(book).data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_book(request, book_id):
    """
    Xoá sách và dọn file (cover/pdf) ra khỏi storage.
    """
    book = get_object_or_404(Book, id=book_id)
    try:
        # Xoá file vật lý (nếu có) trước
        if book.cover_image:
            book.cover_image.delete(save=False)
        if book.pdf_file:
            book.pdf_file.delete(save=False)
        book.delete()
        return Response({"message": "Book deleted successfully"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": f"Failed to delete book: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ================= QUESTION APIs =================
@api_view(['GET'])
def get_questions_by_book(request, book_id):
    """
    Lấy danh sách câu hỏi theo book_id
    """
    questions = Question.objects.filter(book_id=book_id).order_by('order_num')
    serializer = QuestionListSerializer(questions, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_question(request):
    """
    Tạo một câu hỏi mới (chỉ admin hoặc người có quyền)
    """
    serializer = QuestionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_question(request, question_id):
    """
    Cập nhật một câu hỏi (chỉ admin hoặc người có quyền)
    """
    question = get_object_or_404(Question, id=question_id)
    serializer = QuestionSerializer(question, data=request.data, partial=False)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_question(request, question_id):
    """
    Xóa một câu hỏi (chỉ admin hoặc người có quyền)
    """
    question = get_object_or_404(Question, id=question_id)
    question.delete()
    return Response({"message": "Question deleted successfully"}, status=status.HTTP_200_OK)


# ================= QUIZ SESSION APIs =================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_quiz(request, book_id):
    """
    Bắt đầu một phiên làm quiz cho một cuốn sách.
    Trả về:
    - thông tin phiên quiz (session)
    - danh sách câu hỏi để làm bài
    """
    book = get_object_or_404(Book, id=book_id)
    questions = Question.objects.filter(book=book).order_by('order_num')

    if not questions.exists():
        return Response(
            {"error": "No questions available for this book"},
            status=status.HTTP_400_BAD_REQUEST
        )

    quiz_session = QuizSession.objects.create(
        user=request.user,
        book=book,
        total_questions=questions.count()
    )

    session_data = QuizSessionSerializer(quiz_session).data
    questions_data = QuestionListSerializer(questions, many=True).data

    return Response(
        {
            "session": session_data,
            "questions": questions_data,
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_quiz_session(request, session_id):
    """
    Lấy thông tin chi tiết của một phiên làm quiz:
    - thông tin session (score, completed, ...)
    - danh sách câu hỏi của book
    - các câu trả lời đã nộp (user_answers)
    """
    quiz_session = get_object_or_404(QuizSession, id=session_id, user=request.user)

    # Lấy tất cả câu hỏi của cuốn sách này
    questions = Question.objects.filter(book=quiz_session.book).order_by('order_num')

    session_data = QuizSessionSerializer(quiz_session).data
    questions_data = QuestionListSerializer(questions, many=True).data

    return Response(
        {
            "session": session_data,
            "questions": questions_data,
        },
        status=status.HTTP_200_OK
    )
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_quiz_sessions(request):
    """
    Lấy danh sách các phiên làm quiz của user
    """
    quiz_sessions = QuizSession.objects.filter(user=request.user)
    serializer = QuizSessionListSerializer(quiz_sessions, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_answer(request, session_id):
    """
    Nộp câu trả lời cho một câu hỏi trong quiz
    """
    quiz_session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    
    if quiz_session.completed:
        return Response({"error": "Quiz session already completed"}, status=status.HTTP_400_BAD_REQUEST)
    
    question_id = request.data.get('question_id')
    selected_answer = request.data.get('selected_answer')
    
    if not question_id or not selected_answer:
        return Response({"error": "question_id and selected_answer are required"}, status=status.HTTP_400_BAD_REQUEST)
    
    question = get_object_or_404(Question, id=question_id)
    
    # Kiểm tra xem câu hỏi có thuộc về cuốn sách của phiên quiz không
    if question.book != quiz_session.book:
        return Response({"error": "Question does not belong to this quiz"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Kiểm tra định dạng đáp án
    if selected_answer not in ['A', 'B', 'C', 'D']:
        return Response({"error": "Selected answer must be A, B, C, or D"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Kiểm tra xem đã trả lời câu hỏi này chưa
    existing_answer = UserAnswer.objects.filter(quiz_session=quiz_session, question=question).first()
    if existing_answer:
        return Response({"error": "Question already answered"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Tạo bản ghi câu trả lời
    is_correct = (selected_answer == question.correct_answer)
    user_answer = UserAnswer.objects.create(
        quiz_session=quiz_session,
        question=question,
        selected_answer=selected_answer,
        is_correct=is_correct
    )
    
    # Cập nhật điểm nếu trả lời đúng
    if is_correct:
        quiz_session.score = (quiz_session.score or 0) + 1
        quiz_session.save(update_fields=['score'])
    
    serializer = UserAnswerSerializer(user_answer)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_quiz(request, session_id):
    """
    Hoàn thành phiên làm quiz và tính toán điểm số
    """
    quiz_session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    
    if quiz_session.completed:
        return Response({"error": "Quiz session already completed"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Đánh dấu phiên quiz đã hoàn thành
    quiz_session.completed = True
    quiz_session.completed_at = timezone.now()
    quiz_session.save(update_fields=['completed', 'completed_at'])
    
    serializer = QuizSessionSerializer(quiz_session)
    return Response(serializer.data, status=status.HTTP_200_OK)

def test_pdf_notes_view(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    return render(request, "test_pdf_notes.html", {"book": book})

@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_daily_stats(request):
    """
    Returns aggregated stats for the last 14 days:
    - New Users
    - New Books
    - Interactions (Votes)
    """
    days = 14
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days-1)

    # 1. New Users per day
    users_data = (
        User.objects.filter(date_joined__date__gte=start_date)
        .annotate(date=TruncDate('date_joined'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    users_dict = {str(item['date']): item['count'] for item in users_data}

    # 2. New Books per day (using created_at from UserBook)
    books_data = (
        UserBook.objects.filter(created_at__date__gte=start_date)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    books_dict = {str(item['date']): item['count'] for item in books_data}

    # 3. Interactions per day
    interactions_data = (
        NoteInteraction.objects.filter(created_at__date__gte=start_date)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    interactions_dict = {str(item['date']): item['count'] for item in interactions_data}

    # Merge into a list of 14 days
    result = []
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        date_str = str(current_date)
        result.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'new_users': users_dict.get(date_str, 0),
            'new_books': books_dict.get(date_str, 0),
            'interactions': interactions_dict.get(date_str, 0),
        })

    return Response(result)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_system_activity(request):
    """
    Aggegrates recent system activity:
    - User Joins
    - Book Submissions
    - Reviews
    - Flagged Notes (Awful interactions)
    Returns sorted list by timestamp desc.
    """
    limit = 10
    activity_log = []

    # 1. New Users
    users = User.objects.order_by('-date_joined')[:limit]
    for u in users:
        full_name = f"{u.first_name} {u.last_name}".strip()
        activity_log.append({
            'type': 'user_join',
            'timestamp': u.date_joined,
            'message': f"New user joined: {u.username}",
            'user': u.username,
            'full_name': full_name or None
        })

    # 2. Book Submissions
    books = UserBook.objects.order_by('-created_at')[:limit]
    for b in books:
        u_name = b.user.username if b.user else 'Unknown'
        f_name = f"{b.user.first_name} {b.user.last_name}".strip() if b.user else None
        activity_log.append({
            'type': 'book_submit',
            'timestamp': b.created_at,
            'message': f"Book submitted: {b.title}",
            'user': u_name,
            'full_name': f_name or None,
            'details': {'title': b.title, 'status': 'Pending' if not b.is_approved else 'Approved'}
        })

    # 3. Reviews
    reviews = Review.objects.order_by('-created_at')[:limit]
    for r in reviews:
        full_name = f"{r.user.first_name} {r.user.last_name}".strip()
        activity_log.append({
            'type': 'review',
            'timestamp': r.created_at,
            'message': f"Review on {r.book.title}",
            'user': r.user.username,
            'full_name': full_name or None,
            'details': {'rating': r.rating, 'book': r.book.title}
        })

    # 4. Flagged Notes (Interactions where type='awful')
    flags = NoteInteraction.objects.filter(interaction_type='awful').order_by('-created_at')[:limit]
    for f in flags:
        full_name = f"{f.user.first_name} {f.user.last_name}".strip()
        activity_log.append({
            'type': 'flag',
            'timestamp': f.created_at,
            'message': f"Flagged note on {f.note.book.title}",
            'user': f.user.username,
            'full_name': full_name or None,
            'details': {'book': f.note.book.title}
        })

    # Sort by timestamp desc
    activity_log.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Return top 50 mixed events
    return Response(activity_log[:50])