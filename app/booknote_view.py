# ================= BOOK NOTES APIs =================
from django.shortcuts import get_object_or_404
from django.db.models import  Count
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from rest_framework import status, permissions, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import Book,BookNote
from .serializers import (
    BookSerializer, BookNoteSerializer, BookNoteListSerializer
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_book_note(request, book_id):
    """Tạo note mới cho một cuốn sách"""
    book = get_object_or_404(Book, id=book_id)
    
    data = dict(request.data)
    data['book'] = book.id
    
    serializer = BookNoteSerializer(data=data, context={'request': request})
    
    if serializer.is_valid():
        serializer.save(user=request.user, book=book)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_book_notes(request, book_id):
    """Lấy tất cả notes của user cho một cuốn sách"""
    book = get_object_or_404(Book, id=book_id)
    notes = BookNote.objects.filter(user=request.user, book=book).order_by('page_number', 'position_start')
    
    serializer = BookNoteListSerializer(notes, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_note_detail(request, book_id, note_id):
    """Lấy chi tiết một note cụ thể"""
    note = get_object_or_404(BookNote, id=note_id, book_id=book_id, user=request.user)
    serializer = BookNoteSerializer(note)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_book_note(request, book_id, note_id):
    """Cập nhật note (chỉ user sở hữu note mới được phép)"""
    note = get_object_or_404(BookNote, id=note_id, book_id=book_id, user=request.user)
    
    serializer = BookNoteSerializer(note, data=request.data, partial=(request.method == 'PATCH'), context={'request': request})
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_book_note(request, book_id, note_id):
    """Xóa note (chỉ user sở hữu note mới được phép)"""
    note = get_object_or_404(BookNote, id=note_id, book_id=book_id, user=request.user)
    note.delete()
    
    return Response({"message": "Note deleted successfully"}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_personalized_book_content(request, book_id):
    """
    Lấy thông tin sách + tất cả notes của user cho sách đó (Version 2)
    """
    book = get_object_or_404(Book, id=book_id)
    
    book_data = BookSerializer(book).data
    
    notes = BookNote.objects.filter(user=request.user, book=book).order_by('page_number', 'position_start')
    notes_data = BookNoteListSerializer(notes, many=True).data
    
    pdf_url = None
    if book.pdf_file:
        pdf_url = request.build_absolute_uri(book.pdf_file.url)
    
    return Response({
        "book": book_data,
        "pdf_url": pdf_url,
        "notes": notes_data,
        "notes_count": len(notes_data)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_public_book_notes(request, book_id):
    """Lấy tất cả notes công khai (is_public=True) của users khác cho một cuốn sách"""
    book = get_object_or_404(Book, id=book_id)
    notes = BookNote.objects.filter(book=book, is_public=True).order_by('page_number', 'position_start')
    
    serializer = BookNoteListSerializer(notes, many=True)
    return Response({
        "book_id": book.id,
        "book_title": book.title,
        "public_notes": serializer.data,
        "count": len(serializer.data)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_user_notes(request):
    """Lấy tất cả notes của user hiện tại, từ tất cả các sách"""
    notes = BookNote.objects.filter(user=request.user).select_related('book').order_by('-created_at')
    serializer = BookNoteSerializer(notes, many=True)
    
    return Response({
        "notes": serializer.data,
        "total_notes": len(serializer.data)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_notes_statistics(request):
    """Thống kê notes của user"""
    notes = BookNote.objects.filter(user=request.user)
    total_notes = notes.count()
    
    books_with_notes = notes.values('book').distinct().count()
    
    most_noted_book = (
        notes.values('book')
        .annotate(note_count=Count('id'))
        .order_by('-note_count')
        .first()
    )
    
    most_noted_book_info = None
    if most_noted_book:
        try:
            book = Book.objects.get(id=most_noted_book['book'])
            most_noted_book_info = {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "note_count": most_noted_book['note_count']
            }
        except Book.DoesNotExist:
            pass
    
    return Response({
        "total_notes": total_notes,
        "books_with_notes": books_with_notes,
        "most_noted_book": most_noted_book_info,
        "public_notes_count": notes.filter(is_public=True).count(),
        "private_notes_count": notes.filter(is_public=False).count()
    }, status=status.HTTP_200_OK)