from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import BookNote, NoteComment
from .serializers import NoteCommentSerializer

# Pagination configuration
class CommentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    allow_empty_first_page = True
    page_size_query_param = 'page_size'

    def paginate_queryset(self, queryset, request, view=None):
        """
        Override to allow empty first page without 404
        """
        try:
            return super().paginate_queryset(queryset, request, view=view)
        except Exception:
            # If invalid page (or empty), return empty list instead of 404 exception if possible,
            # but DRF NotFound might be raised.
            # actually explicit allow_empty_first_page property usually handles it.
            return []

    # Actually better just set the property:
    allow_empty_first_page = True

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def note_comments(request, note_id):
    """
    GET: List comments for a note (Paginated).
    POST: Create a new comment.
    """
    note = get_object_or_404(BookNote, id=note_id)

    if request.method == 'GET':
        # Filter only active comments (not soft-deleted)
        queryset = NoteComment.objects.filter(note=note, is_deleted=False).order_by('created_at')
        
        paginator = CommentPagination()
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = NoteCommentSerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    elif request.method == 'POST':
        # Simple rate limit check could be added here
        
        serializer = NoteCommentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(note=note)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_comment(request, comment_id):
    """
    Soft delete a comment.
    Permission: Owner OR Admin.
    """
    comment = get_object_or_404(NoteComment, id=comment_id)
    
    # Check permissions
    is_owner = comment.user == request.user
    is_admin = request.user.is_staff or request.user.is_superuser
    
    if not (is_owner or is_admin):
        return Response(
            {"detail": "You do not have permission to delete this comment."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Perform Soft Delete
    comment.is_deleted = True
    comment.deleted_at = timezone.now()
    comment.deleted_by = request.user
    comment.save()
    
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_comments(request):
    """
    Admin Only: List all comments (including deleted ones) for moderation.
    """
    if not request.user.is_staff:
        return Response(status=status.HTTP_403_FORBIDDEN)
        
    # Order by newest first
    queryset = NoteComment.objects.all().order_by('-created_at')
    
    paginator = CommentPagination()
    result_page = paginator.paginate_queryset(queryset, request)
    
    # We can reuse the same serializer or create a AdminCommentSerializer with more info
    # For now, reuse NoteCommentSerializer + extra data if needed
    serializer = NoteCommentSerializer(result_page, many=True, context={'request': request})
    
    return paginator.get_paginated_response(serializer.data)
