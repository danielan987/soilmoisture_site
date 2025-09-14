from django import forms

PARAM_CHOICES = [
    ('GWETPROF', 'Ground Wetness (GWETPROF)'),
    ('PRECTOTCORR', 'Precipitation (PRECTOTCORR)'),
    ('T2M', 'Temperature 2m (T2M)'),
    ('WS10M', 'Wind 10m (WS10M)'),
]

class MainForm(forms.Form):
    query = forms.CharField(
        label='Search location',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'City, address, or "lat,lon"'})
    )
    lat = forms.FloatField(initial=43.6532)   # Toronto default
    lon = forms.FloatField(initial=-79.3832)
    label = forms.CharField(label='Location label', required=False)

    start = forms.CharField(initial='20230825')  # YYYYMMDD
    end   = forms.CharField(initial='20250825')  # YYYYMMDD (today default)
    parameter = forms.ChoiceField(choices=PARAM_CHOICES, initial='GWETPROF')
