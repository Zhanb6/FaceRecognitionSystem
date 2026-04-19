from django.contrib import admin
from .models import Company, CustomUser, PersonFace, RecognitionLog, AuditLog

admin.site.register(Company)
admin.site.register(CustomUser)
admin.site.register(PersonFace)
admin.site.register(RecognitionLog)
admin.site.register(AuditLog)
