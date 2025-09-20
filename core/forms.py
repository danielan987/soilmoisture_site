from django import forms

class CounterForm(forms.Form):
    value = forms.IntegerField(min_value=0, initial=0, required=True)

