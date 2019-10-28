import os

from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.openapi import ReferenceResolver
from drf_yasg.utils import get_consumes, get_produces
from rest_framework.settings import api_settings


class GoogleEndpointSchemaGenerator(OpenAPISchemaGenerator):
    """
    Custom generator for compatibility w/ Google Cloud Endpoints format.
    Preferably CORS
    """
    def get_schema(self, request=None, public=False):
        """
        allow CORS in Google Cloud Endpoint
        """
        endpoints = self.get_endpoints(request)
        components = ReferenceResolver(openapi.SCHEMA_DEFINITIONS,
                                       force_init=True)
        extra = dict(components)
        extra['x-google-endpoints'] = [
            {'name': f"\"{os.environ.get('OPENAPI_HOST')}\"",
             'allowCors': True}
        ]
        extra['x-google-allow'] = 'all'
        self.consumes = get_consumes(api_settings.DEFAULT_PARSER_CLASSES)
        self.produces = get_produces(api_settings.DEFAULT_RENDERER_CLASSES)
        paths, prefix = self.get_paths(endpoints, components, request, public)

        security_definitions = self.get_security_definitions()
        if security_definitions:
            security_requirements = self.get_security_requirements(
                security_definitions)
        else:
            security_requirements = None

        url = self.url
        if url is None and request is not None:
            url = request.build_absolute_uri()

        return openapi.Swagger(
            info=self.info, paths=paths, consumes=self.consumes or None,
            produces=self.produces or None,
            security_definitions=security_definitions,
            security=security_requirements,
            _url=url, _prefix=prefix, _version=self.version, **extra,
        )
