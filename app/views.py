from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import Avg, Q, Count
from django.core.mail import send_mail
from django.core.cache import cache
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from rest_framework import status, permissions, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Book, FavoriteBook, ReadingHistory, UserBook, Review
from .serializers import (
    BookSerializer, ReviewSerializer, FavoriteBookSerializer,
    ReadingHistorySerializer, ResetPasswordSerializer, ChangePasswordSerializer,
    UserBookSerializer
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
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Email already exists!'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(
            username=username, email=username, password=password,
            first_name=first_name, last_name=last_name
        )
        return Response({'message': 'User registered successfully!'}, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    def post(self, request):
        data = request.data
        email = data.get('email'); password = data.get('password')
<<<<<<< HEAD
=======

>>>>>>> giabao
        try:
            user = User.objects.get(email=email)
            auth_user = authenticate(request, username=user.username, password=password)
            if auth_user is None:
                return Response({'message': 'Invalid password!'}, status=status.HTTP_401_UNAUTHORIZED)
<<<<<<< HEAD
            refresh = RefreshToken.for_user(auth_user)
            return Response({
                'token': str(refresh.access_token),
=======

            refresh = RefreshToken.for_user(auth_user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),   # <--- thêm dòng này
>>>>>>> giabao
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
        'pdf_url': request.build_absolute_uri(book.pdf_file.url),
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
    ReadingHistory.objects.create(user=request.user, book=book)
    return Response({"message": "Book added to reading history"}, status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_reading_history(request):
    history = ReadingHistory.objects.filter(user=request.user).order_by('-read_at')
    return Response(ReadingHistorySerializer(history, many=True).data)

# ================= ADMIN LISTS =================
@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_users(request):
    users = User.objects.all()
    data = [{'id': u.id, 'username': u.username, 'email': u.email, 'is_staff': u.is_staff} for u in users]
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_books(request):
    books = Book.objects.all()
    data = [{
        'id': b.id, 'title': b.title, 'author': b.author,
        'pdf_url': (request.build_absolute_uri(b.pdf_file.url) if b.pdf_file else None),
        'pages': b.pages,
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
    total_books = Book.objects.count()
    total_reads = ReadingHistory.objects.count()

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

    total_users = User.objects.count()
    stats = Review.objects.aggregate(total=Count('id'), avg=Avg('rating'))
    average_rating = round(stats['avg'] or 0, 2)

    return Response({
        "total_books": total_books,
        "total_reads": total_reads,
        "most_read_book": most_read_book,
        "total_users": total_users,
        "total_reviews": stats['total'] or 0,
        "average_rating": average_rating,
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

@api_view(['PUT'])
@permission_classes([IsAdminUser])
def update_user(request, user_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    data = request.data
    user.username = data.get('username', user.username)
    user.email = data.get('email', user.email)
    if 'password' in data and data['password']:
        user.set_password(data['password'])
    user.save()

    return Response({"id": user.id, "username": user.username, "email": user.email},
                    status=status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_user(request, user_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    user.delete()
    return Response({"message": "User deleted successfully"}, status=status.HTTP_200_OK)

# ================= CRUD books =================
api_view(['PUT'])  # hoặc ['PATCH'] nếu muốn cập nhật từng phần
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
<<<<<<< HEAD
            
=======

>>>>>>> giabao
        book.delete()
        return Response({"message": "Book deleted successfully"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": f"Failed to delete book: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)