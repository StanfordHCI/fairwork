from django.db import models

class HITType(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    def __str__(self):
        return self.id

class HIT(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    hit_type = models.ForeignKey(HITType, on_delete=models.CASCADE)
    def __str__(self):
        return self.id

class Worker(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    def __str__(self):
        return self.id

class Assignment(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    hit = models.ForeignKey(HIT, on_delete=models.CASCADE)
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)

    SUBMITTED = 's'
    ACCEPTED = 'a'
    REJECTED = 'r'
    OPEN = 'o'
    STATUS_CHOICES = (
        (SUBMITTED, 'submitted'),
        (ACCEPTED, 'accepted'),
        (REJECTED, 'rejected'),
        (OPEN, 'open'),
    )
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=OPEN)
    timestamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.id

class AssignmentDuration(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    duration = models.DurationField()
    timestamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.duration

class AssignmentAudit(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    effective_rate = models.FloatField()

    UNPAID = 'u'
    PAID = 'p'
    NO_PAYMENT_NEEDED = 'n'
    STATUS_CHOICES = (
        (UNPAID, 'unpaid'),
        (PAID, 'paid'),
        (NO_PAYMENT_NEEDED, 'no payment needed')
    )
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=UNPAID)
    timestamp = models.DateTimeField(auto_now=True)
