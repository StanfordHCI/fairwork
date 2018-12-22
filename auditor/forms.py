from django import forms
import boto3
from botocore.exceptions import ClientError
from django.utils.functional import cached_property

class RequesterForm(forms.Form):
    key = forms.CharField(label='AWS Access Key ID', widget=forms.TextInput(attrs={'placeholder': 'AKIAIOSFODNN7EXAMPLE', 'size': 45}), max_length=100)
    secret = forms.CharField(label='AWS Secret Access Key', widget=forms.TextInput(attrs={'placeholder': 'wJalrXUtnFEMIYEXAMPLEKEY', 'size': 45}), max_length=100)
    email = forms.EmailField(label='Email address', widget=forms.EmailInput(attrs={'placeholder': 'williampayfair@gmail.com', 'size': 45}))
    irb_agree = forms.BooleanField(label='I agree to the IRB')

    @cached_property
    def aws_account(self):
        try:
            print("Getting AWS")
            client = boto3.client("sts", aws_access_key_id=self.cleaned_data['key'], aws_secret_access_key=self.cleaned_data['secret'])
            aws_account = client.get_caller_identity()["Account"]
            return aws_account
        except ClientError:
            return None


    def clean(self):
        if self.aws_account is None:
            raise forms.ValidationError('Your AWS keys are incorrect. Please check them and try again.', code="aws_account")
