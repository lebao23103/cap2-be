# app/urls.py
from django.urls import path
from . import views
from .chatbot_view import chat_send, conversations_list, conversation_messages, conversation_end
from .booknote_view import create_book_note, get_user_book_notes, get_note_detail, update_book_note, delete_book_note, get_public_book_notes, get_personalized_book_content, get_all_user_notes, get_user_notes_statistics
urlpatterns = [
    path('', views.home, name='home'),

    # ===== Auth (giữ nguyên) =====
    path('api/register/', views.RegisterView.as_view(), name='register'),
    path('api/login/', views.LoginView.as_view(), name='login'),
    path('api/logout/', views.LogoutView.as_view(), name='logout'),
    path('api/forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('api/reset-password/', views.ResetPasswordView.as_view(), name='reset_password'),

    # ===== Book APIs (khớp views hiện tại) =====
    path('api/search-books/', views.search_books, name='search-books'),
    path('api/books/', views.all_books, name='all_books'),
    path('api/books/<int:book_id>/', views.book_detail_view, name='book_detail_view'),
    path('api/books/<int:book_id>/content/', views.book_content_by_id, name='book_content_by_id'),
    path('api/books/author/<str:author_name>/', views.books_by_author, name='books_by_author'),

    # ===== Reviews =====
    path('api/books/<int:book_id>/add_review/', views.add_review, name='add_review'),
    path('api/books/<int:book_id>/reviews/', views.get_book_reviews, name='get_book_reviews'),

    # ===== User profile =====
    path('user/profile/<int:user_id>/', views.get_user_profile, name='get-user-profile'),
    path('api/user/profile/update/<int:user_id>/', views.update_user_profile, name='update_user'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),

    # ===== Favorites & Reading history =====
    path('api/favorites/', views.get_favorites, name='get_favorites'),
    path('api/favorites/add_to_favorites/', views.add_to_favorites, name='add_to_favorites'),
    path('api/favorites/remove_from_favorites/', views.remove_from_favorites, name='remove_from_favorites'),
    path('api/reading-history/add/', views.add_to_reading_history, name="add_to_reading_history"),
    path('api/reading-history/', views.get_reading_history, name="reading-history"),

    # ===== Admin dashboard & stats =====
    path('api/admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('api/rating-statistics/', views.rating_statistics, name='rating-statistics'),
    path('api/report-statistics/', views.report_statistics, name='report_statistics'),

    path('api/user-roles-statistics/', views.user_roles_statistics, name='user-roles-statistics'),
    path('api/books/total/', views.total_books, name='total-books'),


    # ===== Admin lists + CRUD users =====
    path('api/admin/users/', views.list_users, name='list_users'),
    path('api/admin/books/', views.list_books, name='list_books'),
    path('api/admin/users/create/', views.create_user, name='create_user'),
    path('api/admin/users/<int:user_id>/update/', views.update_user, name='update_user'),
    path('api/admin/users/<int:user_id>/delete/', views.delete_user, name='delete_user'),

    # ===== Book edit/delete =====
    path('api/books/<int:pk>/edit/', views.edit_book_fields, name='edit-book-fields'),
    path('api/books/<int:book_id>/delete/', views.delete_book, name='delete_book'),

    # ===== UserBook moderation =====
    path('api/create-user-book/', views.CreateUserBookView.as_view(), name='create_user_book'),
    path('api/list-user-books/', views.ListUserBooksView.as_view(), name='list_user_books'),
    path('api/approve-user-book/<int:user_book_id>/', views.ApproveUserBookView.as_view(), name='approve-user-book'),
    path('api/reject-delete-book/<int:book_id>/', views.RejectAndDeleteBookView.as_view(), name='reject-delete-book'),
    path('api/list-approved-books/', views.ListApprovedBooksView.as_view(), name='list-approved-books'),
    # ===== Chatbot endpoints =====
    path("chat/send", chat_send),
    path("chat/conversations", conversations_list),
    path("chat/conversations/<uuid:conversation_id>/messages", conversation_messages),
    path("chat/conversations/<uuid:conversation_id>/end", conversation_end),
    
       # ================= BOOK NOTES APIs =================
    
    # --- Create & List Notes ---
    path('api/books/<int:book_id>/notes/', get_user_book_notes, name='get_user_book_notes'),
    path('api/books/<int:book_id>/notes/create/', create_book_note, name='create_book_note'),
    
    # --- Single Note Operations ---
    path('api/books/<int:book_id>/notes/<int:note_id>/',get_note_detail, name='get_note_detail'),
    path('api/books/<int:book_id>/notes/<int:note_id>/update/', update_book_note, name='update_book_note'),
    path('api/books/<int:book_id>/notes/<int:note_id>/delete/', delete_book_note, name='delete_book_note'),
    
    # --- Personalized Reading (Version 2) ---
    path('api/books/<int:book_id>/personalized/', get_personalized_book_content, name='get_personalized_book_content'),
    
    # --- Public Notes ---
    path('api/books/<int:book_id>/notes/public/', get_public_book_notes, name='get_public_book_notes'),
    
    # --- User Notes Management ---
    path('api/my-notes/', get_all_user_notes, name='get_all_user_notes'),
    path('api/my-notes/stats/', get_user_notes_statistics, name='get_user_notes_statistics'),
    
]