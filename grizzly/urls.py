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
from django.conf.urls import url, include
from django.contrib import admin

from loginsvc.views import login, logout, refresh_access_token
from report import views as report


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^v1/', include('account.urls'), name='accounts'),
    url(r'^v1/', include('promotion.urls'), name='promotions'),

    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    # dashboard apis without routers
    url(r'^manage/login/$', login, name='dashboard_login'),
    url(r'^manage/login/refresh/', refresh_access_token,
        name='dashboard_refresh'),

    url(r'^logout/$', logout, name='account_logout'),

    url(r'^report/', report.export_report, name='export_report'),
]
