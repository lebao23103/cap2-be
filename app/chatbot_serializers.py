# app/chat/serializers.py (hoặc trong serializers.py hiện tại)
from rest_framework import serializers
from .models import ChatConversation, ChatMessage

class ChatSendSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    message = serializers.CharField(max_length=4000)
    role = serializers.CharField(required=False, allow_blank=True, default="helpful assistant")

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ("role", "content", "created_at")

class ChatConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatConversation
        fields = ("id", "title", "role", "is_active", "created_at", "updated_at")
