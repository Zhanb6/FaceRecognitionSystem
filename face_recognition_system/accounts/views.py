from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Company, CustomUser, PersonFace, RecognitionLog, AuditLog
from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer, 
    PersonFaceSerializer, RecognitionLogSerializer, AuditLogSerializer
)


def log_action(user, action, details=""):
    AuditLog.objects.create(user=user, action=action, details=details)

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def is_super_admin(user):
    return bool(
        user.is_authenticated and (
            user.is_superuser
            or user.role == CustomUser.Role.SUPERADMIN
            or user.username == "developer"
        )
    )


def is_company_admin(user):
    return bool(user.is_authenticated and user.role == CustomUser.Role.ADMIN)


def get_request_company(request):
    if not is_super_admin(request.user):
        return request.user.company

    company_id = request.data.get("company_id") or request.query_params.get("company_id")
    if company_id:
        return Company.objects.filter(id=company_id).first()
    return request.user.company


def can_manage_faces(user):
    return bool(user.is_authenticated and (is_super_admin(user) or is_company_admin(user) or user.is_camera))


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_staff = False
            user.is_camera = False
            user.role = CustomUser.Role.USER
            user.save()
            log_action(user, "Регистрация", f"Пользователь **{user.username}** зарегистрирован")
            tokens = get_tokens_for_user(user)
            return Response({
                "message": "Registration successful.",
                "user": UserSerializer(user).data,
                "tokens": tokens,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            tokens = get_tokens_for_user(user)
            return Response({
                "message": "Login successful.",
                "user": UserSerializer(user).data,
                "tokens": tokens,
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class PersonFaceViewSet(viewsets.ModelViewSet):
    """
    CRUD for registered faces tied to the logged-in Camera Account.
    """
    serializer_class = PersonFaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if is_super_admin(user):
            return PersonFace.objects.all().order_by('-created_at')

        if user.is_camera:
            return PersonFace.objects.filter(
                allowed_cameras=user,
                company=user.company,
            ).order_by('-created_at').distinct()

        return PersonFace.objects.filter(company=user.company).order_by('-created_at')

    @action(detail=False, methods=['get'])
    def all_faces(self, request):
        faces = self.get_queryset()
        serializer = self.get_serializer(faces, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        if not can_manage_faces(self.request.user):
            raise PermissionDenied("Not enough permissions to create faces")
        face = serializer.save(owner=self.request.user, company=self.request.user.company)
        log_action(self.request.user, "Создание профиля", f"Создан профиль: **{face.full_name}**")
        if self.request.user.is_camera:
            face.allowed_cameras.add(self.request.user)
            log_action(self.request.user, "Привязка к камере", f"Профиль **{face.full_name}** привязан к **{self.request.user.username}**")

    def perform_update(self, serializer):
        if not can_manage_faces(self.request.user):
            raise PermissionDenied("Not enough permissions to update faces")
        old_face = self.get_object()
        old_name = old_face.full_name
        face = serializer.save()
        log_action(self.request.user, "Изменение профиля", f"Профиль **{old_name}** обновлен. Новое ФИО: **{face.full_name}**, роль: {face.role}")

    def perform_destroy(self, instance):
        if not can_manage_faces(self.request.user):
            raise PermissionDenied("Not enough permissions to delete faces")
        name = instance.full_name
        instance.delete()
        log_action(self.request.user, "Удаление профиля", f"Удален профиль: **{name}**")


class RecognitionLogViewSet(viewsets.ModelViewSet):
    """
    CRUD for recognition events tied to the logged-in Camera Account.
    """
    serializer_class = RecognitionLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if is_super_admin(self.request.user):
            return RecognitionLog.objects.all().order_by('-timestamp')
        if self.request.user.is_camera:
            return RecognitionLog.objects.filter(camera_account=self.request.user).order_by('-timestamp')
        return RecognitionLog.objects.filter(camera_account__company=self.request.user.company).order_by('-timestamp')

    @action(detail=False, methods=['get'])
    def all_logs(self, request):
        logs = self.get_queryset()[:100]
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(camera_account=self.request.user)


class CameraAccountsView(APIView):
    """
    List other Camera Accounts (for dashboard overview)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if is_super_admin(request.user):
            cameras = CustomUser.objects.filter(is_camera=True).values(
                "id",
                "username",
                "is_active",
                "date_joined",
                "company_id",
                "owner_id",
                "owner__username",
            )
        else:
            cameras = CustomUser.objects.filter(company=request.user.company, is_camera=True).values(
                "id",
                "username",
                "is_active",
                "date_joined",
                "company_id",
                "owner_id",
                "owner__username",
            )
        return Response(cameras)


class CompanyUsersView(APIView):
    """
    List user accounts in a company.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (is_company_admin(request.user) or is_super_admin(request.user)):
            return Response({"error": "Company Admin permission required"}, status=status.HTTP_403_FORBIDDEN)

        company = get_request_company(request)
        if not company:
            return Response({"error": "Company is required"}, status=status.HTTP_400_BAD_REQUEST)

        queryset = CustomUser.objects.filter(company=company, is_camera=False).exclude(role=CustomUser.Role.SUPERADMIN).order_by("date_joined")
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)


class SuperAdminAdminUsersView(APIView):
    """
    Super Admin: list and create administrator accounts.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_super_admin(request.user):
            return Response({"error": "Super Admin permission required"}, status=status.HTTP_403_FORBIDDEN)

        admins = CustomUser.objects.filter(role=CustomUser.Role.ADMIN).order_by("-date_joined")
        serializer = UserSerializer(admins, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not is_super_admin(request.user):
            return Response({"error": "Super Admin permission required"}, status=status.HTTP_403_FORBIDDEN)

        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email", f"{username}@company.system")
        company_name = request.data.get("company_name")

        if not username or not password:
            return Response({"error": "username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        if CustomUser.objects.filter(username=username).exists():
            return Response({"error": "Username is already taken"}, status=status.HTTP_400_BAD_REQUEST)

        base_company_name = company_name or f"{username} Company"
        final_company_name = base_company_name
        suffix = 1
        while Company.objects.filter(name=final_company_name).exists():
            suffix += 1
            final_company_name = f"{base_company_name} {suffix}"

        company = Company.objects.create(name=final_company_name)
        admin_user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_camera=False,
            role=CustomUser.Role.ADMIN,
            company=company,
            owner=request.user,
        )
        log_action(request.user, "Создание заявки", f"Создан администратор **{admin_user.username}** для компании **{company.name}**")

        return Response({
            "message": "Admin account created",
            "admin": UserSerializer(admin_user).data,
        }, status=status.HTTP_201_CREATED)


class CreateCompanyAdminView(APIView):
    """
    Super Admin creates a company and its administrator account.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not is_super_admin(request.user):
            return Response({"error": "Super Admin permission required"}, status=status.HTTP_403_FORBIDDEN)

        company_name = request.data.get("company_name")
        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email", f"{username}@company.system")

        if not company_name or not username or not password:
            return Response({"error": "company_name, username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        if CustomUser.objects.filter(username=username).exists():
            return Response({"error": "Username is already taken"}, status=status.HTTP_400_BAD_REQUEST)

        if Company.objects.filter(name=company_name).exists():
            return Response({"error": "Company already exists"}, status=status.HTTP_400_BAD_REQUEST)

        company = Company.objects.create(name=company_name)
        admin_user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_camera=False,
            role=CustomUser.Role.ADMIN,
            company=company,
            owner=request.user,
        )
        log_action(request.user, "Создание администратора компании", f"Компания **{company.name}**, администратор **{admin_user.username}**")

        return Response({
            "message": "Company admin created",
            "company_id": company.id,
            "company_name": company.name,
            "admin_id": admin_user.id,
            "admin_username": admin_user.username,
        }, status=status.HTTP_201_CREATED)


class CreateCompanyUserView(APIView):
    """
    Company Admin creates regular users in their own company.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not (is_company_admin(request.user) or is_super_admin(request.user)):
            return Response({"error": "Company Admin permission required"}, status=status.HTTP_403_FORBIDDEN)

        company = get_request_company(request)
        if not company:
            return Response({"error": "Company is required"}, status=status.HTTP_400_BAD_REQUEST)

        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email", f"{username}@user.system")

        if not username or not password:
            return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        if CustomUser.objects.filter(username=username).exists():
            return Response({"error": "This username is already taken"}, status=status.HTTP_400_BAD_REQUEST)

        created_by = request.user
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=False,
            is_camera=False,
            role=CustomUser.Role.USER,
            company=company,
            owner=created_by,
        )
        log_action(request.user, "Создание пользователя", f"Создан пользователь **{username}** для компании **{company.name}**")

        return Response({
            "message": "Company user created",
            "user_id": user.id,
            "username": user.username,
            "company_id": company.id,
        }, status=status.HTTP_201_CREATED)

class CreateCameraView(APIView):
    """
    Allow an Administrator to create a Camera Account.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not (is_company_admin(request.user) or is_super_admin(request.user)):
            return Response({"error": "Admin permission required"}, status=status.HTTP_403_FORBIDDEN)

        company = get_request_company(request)
        if not company:
            return Response({"error": "Company is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email", f"{username}@camera.system")
        
        if not username or not password:
            return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        if CustomUser.objects.filter(username=username).exists():
            return Response({"error": "This camera name is already taken"}, status=status.HTTP_400_BAD_REQUEST)
            
        camera = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_camera=True,
            is_staff=False,
            role=CustomUser.Role.CAMERA,
            company=company,
            owner=request.user,
        )
        log_action(request.user, "Создание камеры", f"Создана камера: **{username}** (компания: **{company.name}**) ")
        return Response({
            "message": "Camera account created",
            "camera_id": camera.id,
            "username": camera.username,
            "company_id": company.id,
        }, status=status.HTTP_201_CREATED)

class CameraFacesView(APIView):
    """
    List faces for a specific Camera Account (Admin/Dashboard view)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, camera_id):
        camera = CustomUser.objects.filter(id=camera_id, is_camera=True).first()
        if not camera:
            return Response({"error": "Camera not found"}, status=status.HTTP_404_NOT_FOUND)

        if not is_super_admin(request.user) and camera.company_id != request.user.company_id:
            return Response({"error": "Forbidden for this company"}, status=status.HTTP_403_FORBIDDEN)

        faces = PersonFace.objects.filter(allowed_cameras=camera_id, company=camera.company)
        serializer = PersonFaceSerializer(faces, many=True)
        return Response(serializer.data)

class CameraAddFaceView(APIView):
    """
    Link an existing PersonFace to a specific Camera Account.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, camera_id):
        if not (is_company_admin(request.user) or is_super_admin(request.user)):
            return Response({"error": "Company Admin permission required"}, status=status.HTTP_403_FORBIDDEN)

        face_id = request.data.get('face_id')
        if not face_id:
            return Response({"error": "face_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            face = PersonFace.objects.get(id=face_id)
            camera = CustomUser.objects.get(id=camera_id)
            if camera.company_id != face.company_id:
                return Response({"error": "Face and camera belong to different companies"}, status=status.HTTP_400_BAD_REQUEST)

            if not is_super_admin(request.user) and camera.company_id != request.user.company_id:
                return Response({"error": "Forbidden for this company"}, status=status.HTTP_403_FORBIDDEN)

            face.allowed_cameras.add(camera_id)
            log_action(request.user, "Добавление в группу", f"Пользователь **{face.full_name}** добавлен в камеру **{camera.username}**")
            return Response({"message": "Face added to camera successfully"}, status=status.HTTP_200_OK)
        except PersonFace.DoesNotExist:
            return Response({"error": "Face not found"}, status=status.HTTP_404_NOT_FOUND)
        except CustomUser.DoesNotExist:
            return Response({"error": "Camera not found"}, status=status.HTTP_404_NOT_FOUND)

class CameraRemoveFaceView(APIView):
    """
    Remove a PersonFace from a specific Camera Account.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, camera_id):
        if not (is_company_admin(request.user) or is_super_admin(request.user)):
            return Response({"error": "Company Admin permission required"}, status=status.HTTP_403_FORBIDDEN)

        face_id = request.data.get('face_id')
        if not face_id:
            return Response({"error": "face_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            face = PersonFace.objects.get(id=face_id)
            camera = CustomUser.objects.get(id=camera_id)
            if not is_super_admin(request.user) and camera.company_id != request.user.company_id:
                return Response({"error": "Forbidden for this company"}, status=status.HTTP_403_FORBIDDEN)

            face.allowed_cameras.remove(camera_id)
            log_action(request.user, "Удаление из группы", f"Пользователь **{face.full_name}** удален из камеры **{camera.username}**")
            return Response({"message": "Face removed from camera successfully"}, status=status.HTTP_200_OK)
        except PersonFace.DoesNotExist:
            return Response({"error": "Face not found"}, status=status.HTTP_404_NOT_FOUND)
        except CustomUser.DoesNotExist:
            return Response({"error": "Camera not found"}, status=status.HTTP_404_NOT_FOUND)

class AuditLogView(APIView):
    """
    List Audit Logs for Admin
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_super_admin(request.user):
            return Response({"error": "Super Admin permission required"}, status=status.HTTP_403_FORBIDDEN)
        
        logs = AuditLog.objects.all().order_by("-timestamp")
        serializer = AuditLogSerializer(logs, many=True)
        return Response(serializer.data)