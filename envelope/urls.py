from django.conf.urls import url, include
from envelope import views as envelope_view
from rest_framework import routers


manage_router = routers.DefaultRouter()
manage_router.register(r'envelopelevel',
                       envelope_view.EnvelopeLevelAdminViewset,
                       base_name='manage_envelopelevels')
manage_router.register(r'envelopesetting',
                       envelope_view.EnvelopeSettingAdminViewset,
                       base_name='manage_envelopesettings')
manage_router.register(r'envelopeclaim',
                       envelope_view.EnvelopeClaimAdminViewset,
                       base_name='manage_envelopeclaims')
manage_router.register(r'envelopedeposit',
                       envelope_view.EnvelopeDepositAdminViewset,
                       base_name='manage_envelopedeposits')
manage_router.register(r'rewards',
                       envelope_view.RewardAdminViewset,
                       base_name='manage_rewards')
manage_router.register(r'eventtypes',
                       envelope_view.EventTypeAdminViewset,
                       base_name='manage_eventtypes')
manage_router.register(r'requestlog',
                       envelope_view.RequestLogAdminViewset,
                       base_name='manage_requestlog')


member_router = routers.DefaultRouter()
member_router.register(r'envelopeclaim',
                       envelope_view.EnvelopeClaimMemberViewset,
                       base_name='member_envelopeclaims')
member_router.register(r'envelopelevel',
                       envelope_view.EnvelopeLevelMemberViewset,
                       base_name='member_envelopelevel')
member_router.register(r'deposits',
                       envelope_view.EnvelopeDepositMemberViewset,
                       base_name='member_envelopedeposits')
member_router.register(r'rewards',
                       envelope_view.RewardMemberViewset,
                       base_name='member_rewards')
member_router.register(r'eventtypes',
                       envelope_view.EventTypeMemberViewset,
                       base_name='member_rewards')

urlpatterns = [
    url(r'^manage/envelope/import/',
        envelope_view.import_file, name='envelope_deposit_import'),
    url(r'^manage/', include(manage_router.urls)),
    url(r'^member/', include(member_router.urls)),
]
