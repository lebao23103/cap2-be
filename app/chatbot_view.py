from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .utils.ai_api import ask_mistral
from rest_framework.decorators import api_view, permission_classes
import json

class ChatbotAPIView(APIView):
    """
    API for chatbot interaction using external AI service
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            user_input = request.data.get('message', '')
            role = request.data.get('role', 'book advisor')  # Default role
            
            if not user_input:
                return Response({
                    'error': 'Message is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get AI response using your existing function
            ai_response = ask_mistral(user_input)
            
            if ai_response == "Sorry, I could not respond at the moment.":
                return Response({
                    'error': 'AI service temporarily unavailable'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            return Response({
                'user_message': user_input,
                'ai_response': ai_response,
                'role': role,
                'status': 'success'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chatbot_conversation(request):
    """
    Function-based view for chatbot conversation
    Supports custom role and content configuration
    """
    try:
        data = request.data
        user_message = data.get('message', '')
        custom_role = data.get('role', None)
        conversation_context = data.get('context', [])
        
        if not user_message:
            return Response({
                'error': 'Message field is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # If custom role is provided, create a customized function call
        if custom_role:
            ai_response = ask_mistral_with_custom_role(user_message, custom_role, conversation_context)
        else:
            # Use default book advisor role
            ai_response = ask_mistral(user_message)
        
        return Response({
            'conversation': {
                'user': user_message,
                'ai': ai_response,
                'role': custom_role or 'book advisor',
                'timestamp': request.META.get('HTTP_DATE', 'unknown')
            },
            'status': 'success'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Conversation error: {str(e)}',
            'status': 'failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def ask_mistral_with_custom_role(user_input, custom_role, context=None):
    """
    Enhanced version of ask_mistral with custom role and context support
    """
    from openai import OpenAI
    import os
    
    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1"
    )
    
    try:
        # Build messages array with custom role
        messages = [
            {"role": "system", "content": f"You are a {custom_role}. Be helpful and professional in your responses."}
        ]
        
        # Add conversation context if provided
        if context and isinstance(context, list):
            for msg in context[-5:]:  # Limit to last 5 messages for context
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    messages.append(msg)
        
        # Add current user message
        messages.append({"role": "user", "content": user_input})
        
        response = client.chat.completions.create(
            model="mistral-saba-24b",
            messages=messages,
            temperature=0.7,
            max_tokens=2048
        )
        
        reply = response.choices[0].message.content
        print(f"[✔] Response from {custom_role}:", reply)
        return reply
        
    except Exception as e:
        print(f"[❌] Error calling AI API with custom role: {str(e)}")
        return "Sorry, I could not respond at the moment."


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def multi_turn_chat(request):
    """
    Multi-turn conversation handler
    Maintains conversation history for context
    """
    try:
        data = request.data
        message = data.get('message', '')
        conversation_id = data.get('conversation_id', None)
        role = data.get('role', 'helpful assistant')
        
        if not message:
            return Response({
                'error': 'Message is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Here you could implement conversation storage in database
        # For now, we'll use the conversation history passed from frontend
        conversation_history = data.get('history', [])
        
        # Build context from history
        context_messages = []
        for hist in conversation_history[-10:]:  # Last 10 messages for context
            if 'user' in hist:
                context_messages.append({"role": "user", "content": hist['user']})
            if 'ai' in hist:
                context_messages.append({"role": "assistant", "content": hist['ai']})
        
        # Get AI response with context
        ai_response = ask_mistral_with_custom_role(message, role, context_messages)
        
        return Response({
            'conversation_id': conversation_id or f"conv_{request.user.id}_{hash(message)}",
            'message': {
                'user': message,
                'ai': ai_response,
                'role': role,
                'user_id': request.user.id,
                'username': request.user.username
            },
            'status': 'success'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Multi-turn chat error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)