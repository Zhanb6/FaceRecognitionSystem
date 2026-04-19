from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required")
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", CustomUser.Role.SUPERADMIN)
        return self.create_user(username, email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Этот класс представляет собой как обычных Администраторов,
    так и "Аккаунты камер", за которыми закреплены люди (лица)
    """
    class Role(models.TextChoices):
        SUPERADMIN = "superadmin", "Super Admin"
        ADMIN = "admin", "Company Admin"
        USER = "user", "User"
        CAMERA = "camera", "Camera"

    username = models.CharField(max_length=150, unique=True, verbose_name="Имя аккаунта (Например: Камера 1 - Вход)")
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_camera = models.BooleanField(default=False, verbose_name="Это устройство-камера?")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name="users")
    owner = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name="owned_cameras", verbose_name="Владелец (Аккаунт)")
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    objects = CustomUserManager()

    def __str__(self):
        return self.username


class PersonFace(models.Model):
    """
    Лица (зарегистрированные пользователи), которые закреплены за определенным аккаунтом.
    """
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="owned_faces", null=True, blank=True, verbose_name="Владелец профиля")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name="faces")
    allowed_cameras = models.ManyToManyField(CustomUser, related_name="faces", blank=True)
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    role = models.CharField(max_length=100, default="Студент", verbose_name="Роль (Студент/Препод)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class RecognitionLog(models.Model):
    """
    Лог распознаваний
    """
    camera_account = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="logs")
    person = models.ForeignKey(PersonFace, null=True, blank=True, on_delete=models.SET_NULL)
    unknown_face = models.BooleanField(default=False)
    confidence = models.FloatField(default=0.0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.camera_account.username} -> {self.person.full_name if self.person else 'Unknown'}"

class AuditLog(models.Model):
    """
    История действий (Audit Log)
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.action} @ {self.timestamp}"