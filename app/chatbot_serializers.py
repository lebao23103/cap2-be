from rest_framework import serializers

class ChatbotMessageSerializer(serializers.Serializer):
    message = serializers.CharField(
        max_length=2000,
        help_text="User message to send to the chatbot"
    )
    role = serializers.CharField(
        max_length=100,
        required=False,
        default="book advisor",
        help_text="Custom role for the AI assistant"
    )
    context = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Conversation context for multi-turn chat"
    )

class MultiTurnChatSerializer(serializers.Serializer):
    message = serializers.CharField(
        max_length=2000,
        help_text="User message"
    )
    conversation_id = serializers.CharField(
        max_length=100,
        required=False,
        help_text="Unique conversation identifier"
    )
    role = serializers.CharField(
        max_length=100,
        required=False,
        default="helpful assistant",
        help_text="AI assistant role"
    )
    history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Previous conversation messages"
    )

class ChatbotResponseSerializer(serializers.Serializer):
    user_message = serializers.CharField()
    ai_response = serializers.CharField()
    role = serializers.CharField()
    status = serializers.CharField()
    timestamp = serializers.DateTimeField(required=False)
    
class ConversationSerializer(serializers.Serializer):
    user = serializers.CharField()
    ai = serializers.CharField()
    role = serializers.CharField()
    timestamp = serializers.CharField()