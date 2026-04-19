from rest_framework import serializers
from .models import CustomUser, PersonFace, RecognitionLog, AuditLog
from django.contrib.auth import authenticate


class UserSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = CustomUser
        fields = ("id", "username", "email", "is_staff", "is_camera", "role", "company", "company_name")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ("username", "email", "password", "password_confirm")

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        validated_data.setdefault("role", CustomUser.Role.USER)
        validated_data.setdefault("is_staff", False)
        validated_data.setdefault("is_camera", False)
        user = CustomUser.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        login = data.get("login")
        password = data.get("password")

        user = CustomUser.objects.filter(username=login).first()
        if not user:
            user = CustomUser.objects.filter(email=login).first()

        if user and user.check_password(password):
            data["user"] = user
        else:
            raise serializers.ValidationError("Incorrect Credentials")

        return data


class PersonFaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonFace
        fields = '__all__'


class RecognitionLogSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source='person.full_name', read_only=True)

    class Meta:
        model = RecognitionLog
        fields = '__all__'
        read_only_fields = ('camera_account',)

class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = '__all__'