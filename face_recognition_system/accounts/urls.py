from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, LoginView, ProfileView, PersonFaceViewSet, 
    RecognitionLogViewSet, CameraAccountsView, CameraFacesView, 
    CameraAddFaceView, CreateCameraView, CameraRemoveFaceView,
    AuditLogView, CreateCompanyAdminView, CreateCompanyUserView, CompanyUsersView,
    SuperAdminAdminUsersView
)
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r'faces', PersonFaceViewSet, basename='faces')
router.register(r'logs', RecognitionLogViewSet, basename='logs')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('company-admins/create/', CreateCompanyAdminView.as_view(), name='create_company_admin'),
    path('users/create/', CreateCompanyUserView.as_view(), name='create_company_user'),
    path('users/', CompanyUsersView.as_view(), name='company_users'),
    path('admin-users/', SuperAdminAdminUsersView.as_view(), name='admin_users_list_create'),
    path('cameras/', CameraAccountsView.as_view(), name='cameras'),
    path('cameras/create/', CreateCameraView.as_view(), name='create_camera'),
    path('cameras/<int:camera_id>/faces/', CameraFacesView.as_view(), name='camera_faces'),
    path('cameras/<int:camera_id>/add_face/', CameraAddFaceView.as_view(), name='camera_add_face'),
    path('cameras/<int:camera_id>/remove_face/', CameraRemoveFaceView.as_view(), name='camera_remove_face'),
    path('audit-logs/', AuditLogView.as_view(), name='audit_logs'),
    path('', include(router.urls)),
]