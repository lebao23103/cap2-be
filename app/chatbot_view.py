# app/chat/views.py
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import ChatConversation, ChatMessage
from .chatbot_serializers import (
    ChatSendSerializer, ChatConversationSerializer, ChatMessageSerializer
)

# Dùng hàm gọi AI từ utils/ai_api (đÃ hỗ trợ role + context)
from .utils.ai_api import ask_mistral

# Số message gần nhất dùng làm ngữ cảnh
MAX_CONTEXT_MSG = 12


def generate_ai_reply(user_message: str, role: str, context_messages: list[dict]) -> str:
    """
    Gọi AI bằng API key của bạn thông qua ask_mistral(role, context).
    """
    # Chuẩn hoá context: chỉ nhận role hợp lệ + có content
    safe_ctx = []
    for m in (context_messages or [])[-MAX_CONTEXT_MSG:]:
        if isinstance(m, dict) and m.get("role") in ("system", "user", "assistant") and m.get("content"):
            safe_ctx.append({"role": m["role"], "content": m["content"]})

    custom_role = (role or "helpful assistant").strip()

    # Gọi AI qua utils/ai_api.ask_mistral (đã hỗ trợ role & context)
    return ask_mistral(
        user_input=user_message,
        role=custom_role,
        context=safe_ctx
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat_send(request):
    """
    Gửi 1 tin nhắn. Nếu không có conversation_id -> tạo mới.
    Lưu user msg + assistant msg vào DB và trả về conversation_id + trả lời AI.
    """
    s = ChatSendSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    message = s.validated_data["message"].strip()
    role = s.validated_data.get("role") or "helpful assistant"
    conv_id = s.validated_data.get("conversation_id")

    if not message:
        return Response({"error": "Message is required."}, status=400)

    if conv_id:
        conv = get_object_or_404(ChatConversation, id=conv_id, owner=request.user)
        if not conv.is_active:
            return Response({"error": "Conversation ended."}, status=400)
    else:
        conv = ChatConversation.objects.create(
            owner=request.user,
            role=role,
            title=message[:80]
        )

    # Build context từ DB (lấy ngược rồi đảo lại để đúng thứ tự)
    recent = list(conv.messages.order_by("-created_at")[:MAX_CONTEXT_MSG][::-1])
    context_messages = [{"role": m.role, "content": m.content} for m in recent]

    try:
        ai_text = generate_ai_reply(message, conv.role or role, context_messages)
    except Exception as e:
        # ask_mistral đã tự catch phần lớn lỗi và trả "Sorry, ..."
        # Khối này chỉ bắt lỗi bất ngờ (serialization, etc.)
        return Response({"error": f"AI call failed: {e}"}, status=502)

    with transaction.atomic():
        ChatMessage.objects.create(conversation=conv, role="user", content=message)
        ChatMessage.objects.create(conversation=conv, role="assistant", content=ai_text)
        conv.save(update_fields=["updated_at"])

    return Response({
        "conversation_id": str(conv.id),
        "role": conv.role,
        "message": {"user": message, "ai": ai_text}
    }, status=200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def conversations_list(request):
    qs = ChatConversation.objects.filter(owner=request.user).order_by("-updated_at")[:50]
    return Response(ChatConversationSerializer(qs, many=True).data, status=200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def conversation_messages(request, conversation_id):
    limit = int(request.query_params.get("limit", 50))
    conv = get_object_or_404(ChatConversation, id=conversation_id, owner=request.user)
    msgs = conv.messages.order_by("-created_at")[:limit][::-1]
    return Response({
        "conversation": str(conv.id),
        "items": ChatMessageSerializer(msgs, many=True).data
    }, status=200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def conversation_end(request, conversation_id):
    conv = get_object_or_404(ChatConversation, id=conversation_id, owner=request.user)
    conv.is_active = False
    conv.save(update_fields=["is_active", "updated_at"])
    return Response({"ok": True}, status=200)
