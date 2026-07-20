from django.conf import settings

def sri_settings(request):
    sri_url = getattr(settings, 'SRI_MICROSERVICE_URL', 'https://sri-microservice.vercel.app/firmar-y-enviar')
    base_url = sri_url.rsplit('/', 1)[0]
    return {
        'SRI_MICROSERVICE_CONFIG_URL': f"{base_url}/configurar"
    }
