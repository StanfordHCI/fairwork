from django.db import models
from django.conf import settings


class HITType(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    payment = models.DecimalField(max_digits=6, decimal_places=2)
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
    assignment = models.OneToOneField(Assignment, on_delete=models.CASCADE)
    duration = models.DurationField()
    timestamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%s: %s" % (self.assignment, self.duration)

class AssignmentAudit(models.Model):
    assignment = models.OneToOneField(Assignment, on_delete=models.CASCADE)
    estimated_time = models.DurationField(blank=True, null=True)
    estimated_rate = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    underpayment = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)

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

    def is_underpaid(self):
        # If nobody reported a time, we can't say it's underpaid
        if self.estimated_time is None or self.estimated_rate is None:
            return False
        else:
            return self.estimated_rate < settings.MINIMUM_WAGE_PER_HOUR

    """
    Returns how much money needs to be paid to bring the assignment up to the desired wage rate
    """
    def get_underpayment(self):
        if self.estimated_time is None or self.estimated_rate is None:
            return None

        underpayment_ratio = settings.MINIMUM_WAGE_PER_HOUR / self.estimated_rate
        paid_already = self.assignment.hit.hit_type.payment
        underpayment = paid_already * (underpayment_ratio - 1)
        return underpayment

    def __str__(self):
        s = '%s:\n\tBase pay %.2f\n\t' % (self.assignment, self.assignment.hit.hit_type.payment)
        if self.estimated_time is None or self.estimated_rate is None:
            s += 'Effective time and rate unknown'
        else:
            s += 'Effective rate $%.2f/hr because it took %s\n\t' % (self.estimated_rate, self.estimated_time)
            if self.is_underpaid():
                underpayment_ratio = settings.MINIMUM_WAGE_PER_HOUR / self.estimated_rate
                s += 'Need to multiply base pay by %.2fx to reach $%.2f/hr\n\tBonus %.2f' % (underpayment_ratio, settings.MINIMUM_WAGE_PER_HOUR, self.get_underpayment())
            else:
                s += 'Met or exceeded target rate of $%.2f/hr' % (settings.MINIMUM_WAGE_PER_HOUR)
        return s
