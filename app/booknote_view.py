# ================= BOOK NOTES APIs =================
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from rest_framework import status, permissions, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import Book, BookNote, NoteInteraction
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
    # MODERATION: Only show visible notes
    notes = BookNote.objects.filter(book=book, is_public=True, status='visible').order_by('page_number', 'position_start')
    
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
        "private_notes_count": notes.filter(is_public=False).count(),
        # Add moderation stats if useful for user profile? No, internal only.
    }, status=status.HTTP_200_OK)


# ================= MODERATION APIs =================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vote_note(request, note_id):
    """
    Vote Helpful/Awful for a note.
    Auto-hides note if awful_count >= 5.
    """
    note = get_object_or_404(BookNote, id=note_id)
    user = request.user
    vote_type = request.data.get('type')  # 'helpful' or 'awful'

    if vote_type not in ['helpful', 'awful']:
        return Response({"error": "Invalid vote type"}, status=status.HTTP_400_BAD_REQUEST)

    # Check existing interaction
    interaction = NoteInteraction.objects.filter(user=user, note=note).first()
    
    # Simple logic: Toggle if same, Switch if different
    if interaction:
        if interaction.interaction_type == vote_type:
            # Same vote -> Remove it (Toggle off)
            interaction.delete()
            if vote_type == 'helpful':
                note.helpful_count = max(0, note.helpful_count - 1)
            else:
                note.awful_count = max(0, note.awful_count - 1)
        else:
            # Different vote -> Switch
            old_type = interaction.interaction_type
            interaction.interaction_type = vote_type
            interaction.save()
            
            # Update counts
            if old_type == 'helpful':
                note.helpful_count = max(0, note.helpful_count - 1)
                note.awful_count += 1
            else:
                note.awful_count = max(0, note.awful_count - 1)
                note.helpful_count += 1
    else:
        # New vote
        NoteInteraction.objects.create(user=user, note=note, interaction_type=vote_type)
        if vote_type == 'helpful':
            note.helpful_count += 1
        else:
            note.awful_count += 1

    # AUTO-MODERATION RULE: Threshold = 5
    if note.awful_count >= 5:
        note.status = 'hidden'
    
    note.save()

    return Response({
        "helpful_count": note.helpful_count,
        "awful_count": note.awful_count,
        "status": note.status,
        "user_vote": vote_type if (not interaction or interaction.interaction_type != vote_type) else None # Returns current state
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_flagged_notes(request):
    """
    Admin API to get flagged/hidden notes.
    """
    # Get hidden notes OR notes with any awful votes, sorted by most awful first
    flagged_notes = BookNote.objects.filter(
        Q(status='hidden') | Q(awful_count__gt=0)
    ).order_by('status', '-awful_count') # 'hidden' comes before 'visible' alphabetically? No, h < v. So hidden first.

    # Manual serialization for custom admin view
    data = []
    for note in flagged_notes:
        data.append({
            "id": note.id,
            "content": note.note_content,
            "book_title": note.book.title,
            "user": note.user.username,
            "status": note.status,
            "helpful_count": note.helpful_count,
            "awful_count": note.awful_count,
            "created_at": note.created_at
        })

    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def moderate_note(request, note_id):
    """
    Admin action: Restore or Delete.
    """
    note = get_object_or_404(BookNote, id=note_id)
    action = request.data.get('action') # 'restore' or 'delete'

    if action == 'restore':
        note.status = 'visible'
        # Optional: Reset awful count? Let's NOT reset, history is important.
        # But we must ensure it doesn't auto-hide immediately again next vote.
        # Actually, if we keep awful_count >= 5, the next vote (helpful or awful) might trigger check.
        # So we should probably reset awful_count or have an 'admin_approved' status.
        # For simplicity MVP: Reset awful_count to 0.
        note.awful_count = 0 
        note.save()
        return Response({"message": "Note restored and awful count reset"}, status=status.HTTP_200_OK)
    elif action == 'delete':
        note.delete() # Hard delete
        return Response({"message": "Note permanently deleted"}, status=status.HTTP_200_OK)
    
    return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)