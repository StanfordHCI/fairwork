from django.contrib import admin

from .models import HITType, HIT, Worker, Assignment, AssignmentDuration, AssignmentAudit

admin.site.register(HITType)
admin.site.register(HIT)
admin.site.register(Worker)
admin.site.register(Assignment)
admin.site.register(AssignmentDuration)
admin.site.register(AssignmentAudit)
