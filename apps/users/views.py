from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics

from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """Public endpoint for creating a new account. Open to anyone
    (AllowAny) since a user must be able to register before they can
    authenticate at all."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class LogoutView(APIView):
    """Blacklists a refresh token so it can no longer be used to obtain new
    access tokens — the actual logout mechanism, since JWT access tokens
    can't be revoked individually before they expire."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'Refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {'detail': 'Token is invalid or already blacklisted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_205_RESET_CONTENT)

class MeView(generics.RetrieveUpdateAPIView):
    """Returns/updates the current authenticated user's own profile.
    get_object() always returns request.user, so there's no way to target
    any other user's data through this endpoint — no id is ever accepted
    from the request."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user