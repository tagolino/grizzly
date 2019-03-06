from import_export import resources

from promotion.models import PromotionBet


class PromotionBetResource(resources.ModelResource):
    class Meta:
        model = PromotionBet
