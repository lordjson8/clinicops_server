from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom error responses that match the frontend's expected format:
    {
        "error": "error_code",
        "message": "Human-readable message",
        "details": { "field": ["error"] }
    }
    """

    response = exception_handler(exc,context)

    if response is None:
        return response

    # Bad Request(Validation Error) 400
    if isinstance(response, ValidationError):
        error_data = response.data
         
        # If the serializer returned our custom format already
        if isinstance(error_data, dict) and 'error' in error_data:
            return response
        
        # Otherwise, reshapes DRF's default format
        response.data = {
            'error': "validation_error",
            'message': 'Erreur de validation',
            'details': error_data
        }
    
    # Permission denied (403)
    elif response.status_code == status.HTTP_403_FORBIDDEN:
        detail = getattr(exc, 'detail', 'Permission refusee')
        
        response_data = {
            'error': 'forbidden',
            'message': str(detail),
            # 'details': '',
        }


    # Resource Not found (404)
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        
        response.data = {
            'error': 'not_found',
            'message': 'Ressource introuvable',
        }

    # Throttled (429)
    elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        wait = getattr(exc, 'wait', None)
        msg = 'Trop de requetes.'

        if wait:
            msg += f' Reessayer dans {int(wait)} secondes'
        response.data = {
            'error': 'throttled',
            'message': msg,
        }

    elif response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        response.data = {
            'error': 'method_not_allowed',
            'message': 'Methode non autorisee'
        }

    return response
    