from rest_framework.throttling import SimpleRateThrottle

class LoginThrottle(SimpleRateThrottle):
    """
    Docstring for LoginThrottle

    5 attempts per minute per IP.
    Applied to POST /api/v1/auth/login/
    """

    scope = 'login'
    def get_cache_key(self, request, view):

        # return self.cache_format % {
        #     'scope': self.scope,
        #     'ident' : self.get_ident(request),
        # }
        return super().get_cache_key(request, view)

class RegisterThrottle(SimpleRateThrottle):
    """
    Docstring for RegisterThrottle

    3 attempts per minute per IP.
    Applied to POST /api/v1/auth/register/
    """

    scope = 'register'

    def get_cache_key(self, request, view):
        # return self.cache_format % {
        #     'scope': self.scope,
        #     'ident': self.get_ident(request)
        # }
        return super().get_cache_key(request, view)

class SMSThrottle(SimpleRateThrottle):
    """
    Docstring for SMSThrottle

    3 SMS requests per minute per IP.
    Applied to POST /api/v1/auth/password-reset/
    """
    scope = 'sms'

    def get_cache_key(self, request, view):
        # return self.cache_format % {
        #     'scope': self.scope,
        #     'ident': self.get_ident(request)
        # }
        return super().get_cache_key(request, view)
