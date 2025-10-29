from rest_framework import serializers
from .models import Country

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'capital', 'region', 'population', 
                  'currency_code', 'exchange_rate', 'estimated_gdp', 
                  'flag_url', 'last_refreshed_at']
        read_only_fields = ['id', 'last_refreshed_at']

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("name is required")
        return value

    def validate_population(self, value):
        if value < 0:
            raise serializers.ValidationError("population must be positive")
        return value

    def validate_currency_code(self, value):
        if value and len(value) != 3:
            raise serializers.ValidationError("currency_code must be 3 characters")
        return value