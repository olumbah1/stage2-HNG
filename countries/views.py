from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.db.models import Q, DecimalField
from django.db.models.functions import Cast
import requests
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import os
from .models import Country
from .serializers import CountrySerializer
from django.conf import settings

class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer

    def get_queryset(self):
        qs = Country.objects.all()
        region = self.request.query_params.get('region')
        currency = self.request.query_params.get('currency')
        sort = self.request.query_params.get('sort', '-estimated_gdp')
        
        if region:
            qs = qs.filter(region__iexact=region)
        if currency:
            qs = qs.filter(currency_code__iexact=currency)
        
        if sort == 'gdp_desc':
            qs = qs.order_by('-estimated_gdp')
        elif sort == 'gdp_asc':
            qs = qs.order_by('estimated_gdp')
        elif sort == 'population_desc':
            qs = qs.order_by('-population')
        elif sort == 'population_asc':
            qs = qs.order_by('population')
        
        return qs

    @action(detail=False, methods=['post'])
    def refresh(self, request):
        try:
            # Fetch external data
            countries_data = self._fetch_countries()
            exchange_rates = self._fetch_exchange_rates()
            
            if not countries_data or not exchange_rates:
                return Response(
                    {'error': 'External data source unavailable',
                     'details': 'Could not fetch data from external APIs'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            # Process and store countries
            for country_data in countries_data:
                self._process_country(country_data, exchange_rates)

            # Generate summary image
            self._generate_summary_image()
            
            total = Country.objects.count()
            last_refreshed = Country.objects.first().last_refreshed_at if total > 0 else None

            return Response({
                'message': 'Countries refreshed successfully',
                'total_countries': total,
                'last_refreshed_at': last_refreshed
            })
        except Exception as e:
            return Response(
                {'error': 'External data source unavailable',
                 'details': str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

    def _fetch_countries(self):
        try:
            url = 'https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies'
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f'Could not fetch data from restcountries.com: {str(e)}')

    def _fetch_exchange_rates(self):
        try:
            url = 'https://open.er-api.com/v6/latest/USD'
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json().get('rates', {})
        except requests.exceptions.RequestException as e:
            raise Exception(f'Could not fetch data from open.er-api.com: {str(e)}')

    def _process_country(self, country_data, exchange_rates):
        name = country_data.get('name', '').strip()
        if not name:
            return

        capital = country_data.get('capital', '')
        region = country_data.get('region', '')
        population = country_data.get('population', 0)
        flag_url = country_data.get('flag', '')
        
        # Handle currencies
        currencies = country_data.get('currencies', [])
        currency_code = None
        exchange_rate = None
        estimated_gdp = 0

        if currencies and len(currencies) > 0:
            currency_code = currencies[0].get('code', '').upper()
            if currency_code in exchange_rates:
                exchange_rate = exchange_rates[currency_code]
                multiplier = random.uniform(1000, 2000)
                estimated_gdp = (population * multiplier) / float(exchange_rate)

        country, created = Country.objects.update_or_create(
            name__iexact=name,
            defaults={
                'name': name,
                'capital': capital,
                'region': region,
                'population': population,
                'currency_code': currency_code,
                'exchange_rate': exchange_rate,
                'estimated_gdp': estimated_gdp if estimated_gdp > 0 else None,
                'flag_url': flag_url,
            }
        )

    def _generate_summary_image(self):
        try:
            os.makedirs(settings.CACHE_DIR, exist_ok=True)
            
            top_countries = Country.objects.filter(
                estimated_gdp__isnull=False
            ).order_by('-estimated_gdp')[:5]
            
            total_count = Country.objects.count()
            last_refreshed = Country.objects.values('last_refreshed_at').first()
            
            # Create image
            img = Image.new('RGB', (800, 600), color=(26, 26, 46))
            draw = ImageDraw.Draw(img)
            
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
                header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
                text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except:
                title_font = header_font = text_font = small_font = ImageFont.load_default()

            # Draw title
            draw.text((400, 30), "Country Data Summary", fill=(0, 212, 255), font=title_font, anchor="mm")

            # Draw stats
            draw.text((50, 100), f"Total Countries: {total_count}", fill=(255, 255, 255), font=header_font)
            
            if last_refreshed:
                timestamp = last_refreshed['last_refreshed_at'].strftime("%Y-%m-%d %H:%M:%S")
                draw.text((50, 140), f"Last Refreshed: {timestamp}", fill=(170, 170, 170), font=small_font)

            # Draw top 5
            draw.text((50, 200), "Top 5 by Estimated GDP:", fill=(0, 212, 255), font=header_font)
            
            for idx, country in enumerate(top_countries):
                gdp = float(country.estimated_gdp or 0)
                text = f"{idx + 1}. {country.name} - ${gdp:,.2f}"
                draw.text((70, 240 + idx * 50), text, fill=(255, 255, 255), font=text_font)

            # Save image
            image_path = os.path.join(settings.CACHE_DIR, 'summary.png')
            img.save(image_path)
        except Exception as e:
            print(f"Error generating image: {str(e)}")

    @action(detail=False, methods=['get'])
    def image(self, request):
        image_path = os.path.join(settings.CACHE_DIR, 'summary.png')
        if os.path.exists(image_path):
            return FileResponse(open(image_path, 'rb'), content_type='image/png')
        return Response(
            {'error': 'Summary image not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(detail=False, methods=['get'])
    def status(self, request):
        total = Country.objects.count()
        last_refreshed = Country.objects.values('last_refreshed_at').first()
        return Response({
            'total_countries': total,
            'last_refreshed_at': last_refreshed['last_refreshed_at'] if last_refreshed else None
        })

    def get_object(self):
        name = self.kwargs.get('pk')
        return get_object_or_404(Country, name__iexact=name)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({'message': 'Country deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)