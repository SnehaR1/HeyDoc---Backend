import jwt
import datetime
from django.conf import settings
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from rest_framework.exceptions import AuthenticationFailed
from .models import BlackListedToken


def create_access_token(doc_id):

    payload = {
        "doc_id": doc_id,
        "exp": datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(days=1),
        "iat": datetime.datetime.now(datetime.timezone.utc),
        "type": "access",
    }
    with open("private.pem", "r") as key_file:
        private_key = key_file.read()

    access_token = jwt.encode(payload, private_key, algorithm="RS256")
    return access_token


def create_refresh_token(doc_id):

    refresh_payload = {
        "doc_id": doc_id,
        "exp": datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(days=7),
        "iat": datetime.datetime.now(datetime.timezone.utc),
        "type": "refresh",
    }

    with open("private.pem", "r") as key_file:
        private_key = key_file.read()

    refresh_token = jwt.encode(refresh_payload, private_key, algorithm="RS256")
    return refresh_token


def verify_jwt(token, token_type="access"):
    try:
        if BlackListedToken.objects.filter(token=token).exists():
            raise AuthenticationFailed("Token has been blacklisted")

        with open("public.pem", "r") as key_file:
            public_key = key_file.read()

        payload = jwt.decode(token, public_key, algorithms=["RS256"])

        if payload.get("type") != token_type:
            raise InvalidTokenError("Invalid token type")

        return payload
    except ExpiredSignatureError:
        raise Exception("Token has expired")
    except InvalidTokenError:
        raise Exception("Invalid token")


def refresh_access_token(refresh_token):
    try:
        payload = verify_jwt(refresh_token, token_type="refresh")
        doc_id = payload["doc_id"]
        new_access_token = create_access_token(doc_id)
        return new_access_token
    except Exception as e:
        raise Exception(f"Could not refresh access token: {str(e)}")
