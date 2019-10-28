"""grizzly URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os

from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny
from rest_framework.documentation import include_docs_urls

from .lib.endpoints import GoogleEndpointSchemaGenerator
from loginsvc.views import login, logout, refresh_access_token
from report import views as report


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^v1/', include('account.urls'), name='accounts'),
    url(r'^v1/', include('promotion.urls'), name='promotions'),
    url(r'^v1/', include('envelope.urls'), name='envelopes'),
    url(r'^v1/', include('configsetting.urls'), name='configsetting'),
    url(r'^v1/', include('cms.urls'), name='cms'),
    url(r'^v1/', include('ticket.urls'), name='tickets'),

    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    url(r'^captcha/', include('captcha.urls')),

    # dashboard apis without routers
    url(r'^manage/login/$', login, name='dashboard_login'),
    url(r'^manage/login/refresh/', refresh_access_token,
        name='dashboard_refresh'),

    url(r'^logout/$', logout, name='account_logout'),

    url(r'^report/', report.export_report, name='export_report'),
]

if settings.DEBUG:
    schema_view = get_schema_view(
        openapi.Info(
            title="API Documentation",
            default_version='',
            description='',
            terms_of_service="#",
            contact=openapi.Contact(email='manila@unnotech.com'),
            license=openapi.License(name='BSD License'),
        ),
        f'http://{os.environ.get("OPENAPI_HOST")}',
        public=True,
        generator_class=GoogleEndpointSchemaGenerator,
        permission_classes=(AllowAny,),
    )
    api_docs = [
        url('docs/', include_docs_urls(
            title='API Docs', permission_classes=(AllowAny,))),
        url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(
            cache_timeout=0), name='schema-json'),
        url(r'^swagger/$', schema_view.with_ui(
            'swagger', cache_timeout=0), name='schema-swagger-ui'),
        url(r'^redoc/$', schema_view.with_ui(
            'redoc', cache_timeout=0), name='schema-redoc')
    ]
    urlpatterns += api_docs
