# app/urls.py
from django.urls import path
from . import views
from .chatbot_view import ChatbotAPIView, chatbot_conversation, multi_turn_chat

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

    # ===== AI APIs (giữ nguyên như bạn yêu cầu) =====
    path('api/chatbot/', ChatbotAPIView.as_view(), name='chatbot'),
    path('api/chatbot/conversation/', chatbot_conversation, name='chatbot_conversation'),
    path('api/chatbot/multi-turn/', multi_turn_chat, name='multi_turn_chat'),

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

    # NOTE: Endpoint import Gutenberg theo genre cũ. View đã remove trong views.py mới.
    # Mình GIỮ NGUYÊN dưới dạng comment để bạn tự bật khi cần.
    # path('api/admin/fetch-books-genre/', views.fetch_books_by_genre, name='fetch_books_by_genre'),  # TODO: view đã remove
]
