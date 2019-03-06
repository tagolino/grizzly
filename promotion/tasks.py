import logging

from calendar import monthrange
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.utils import timezone

from account.models import Member
from grizzly.celery import app
from promotion.models import (GAME_TYPE_ELECTRONICS,
                              PromotionBet,
                              PromotionBetLevel,
                              PromotionBetMonthly,
                              Summary)


logger = logging.getLogger(__name__)


@app.task(name='promotion_bet_import')
def promotion_bet_import(import_data, user_id, game_type):
    user = User.objects.get(id=user_id)
    today = timezone.now()
    week_begin = today - timedelta(days=today.weekday())
    week_end = week_begin + timedelta(days=6)
    cycle_year = today.year
    cycle_month = today.month
    month_range = monthrange(cycle_year, cycle_month)
    bet_levels = PromotionBetLevel.objects.all().order_by('total_bet')
    logger.info(user)
    for data in import_data:
        logger.info(data)
        member, created = Member.objects.get_or_create(
            username=data['username'])
        current_week_bonus = 0.0

        if created:
            member.created_by = user
        else:
            member.updated_by = user

        if int(game_type) == GAME_TYPE_ELECTRONICS:
            # For electronic game type (first game type)
            # Will only use the data in Member model
            bet_summary = member
        else:
            # For live_game game type (and other new game type)
            # data will be saved in new model which is
            # the bet summary
            bet_summary, created = Summary.objects.get_or_create(
                member=member, game_type=game_type)

        bet_data = {
            'member': member,
            'username': data['username'],
            'amount': data['amount'],
            'cycle_begin': week_begin,
            'cycle_end': week_end,
            'created_by': user,
            'game_type': game_type,
        }

        bet_summary.total_promotion_bet += float(data['amount'])

        bet_level = bet_levels.filter(
            total_bet__lte=bet_summary.total_promotion_bet,
            game_type=game_type).last()

        if not bet_summary.promotion_bet_level and bet_level:
            levels = bet_levels.filter(total_bet__lte=bet_level.total_bet)
            for _level in levels:
                current_week_bonus += _level.bonus
                bet_summary.total_promotion_bonus += _level.bonus
        elif bet_summary.promotion_bet_level and bet_level:
            if bet_level.total_bet >= \
                    bet_summary.promotion_bet_level.total_bet:
                levels = bet_levels.filter(
                    total_bet__gt=bet_summary.promotion_bet_level.total_bet,
                    total_bet__lte=bet_level.total_bet)
                for _level in levels:
                    current_week_bonus += _level.bonus
                    bet_summary.total_promotion_bonus += _level.bonus
            elif bet_level.total_bet <= \
                    bet_summary.promotion_bet_level.total_bet:
                levels = bet_levels.filter(
                    total_bet__gt=bet_level.total_bet,
                    total_bet__lte=bet_summary.promotion_bet_level.total_bet)
                for _level in levels:
                    current_week_bonus += _level.bonus
                    bet_summary.total_promotion_bonus -= _level.bonus
        elif bet_summary.promotion_bet_level and not bet_level:
            levels = bet_levels.filter(
                total_bet__lte=bet_summary.promotion_bet_level.total_bet)
            for _level in levels:
                current_week_bonus += _level.bonus
                bet_summary.total_promotion_bonus -= _level.bonus

        bet_summary.previous_week_bet_level = bet_summary.promotion_bet_level
        bet_summary.promotion_bet_level = bet_level
        bet_summary.current_week_bonus = current_week_bonus

        bet_data['promotion_bet_level'] = bet_summary.promotion_bet_level

        PromotionBet.objects.create(**bet_data)

        promotion_bet_monthly, created = PromotionBetMonthly.objects.\
            get_or_create(member=member, cycle_year=cycle_year,
                          cycle_month=cycle_month, game_type=game_type)

        if created:
            promotion_bet_monthly.cycle_year = cycle_year
            promotion_bet_monthly.cycle_month = cycle_month
            cycle_begin = month_range[0] or 1
            promotion_bet_monthly.cycle_begin = today.replace(
                day=cycle_begin)
            promotion_bet_monthly.cycle_end = today.replace(day=month_range[1])

            try:
                previous_month = datetime(cycle_year, cycle_month, 1) - \
                    timedelta(days=1)
                previous_month_bet = PromotionBetMonthly.objects.get(
                    member=member, cycle_year=cycle_year,
                    cycle_month=previous_month.month, game_type=game_type)

                bet_summary.previous_month_bet_level = \
                    previous_month_bet.promotion_bet_level
            except PromotionBetMonthly.DoesNotExist:
                logger.error('No promotion level data for previous month.')

        promotion_bet_monthly.total_bet += float(data['amount'])
        promotion_bet_monthly.promotion_bet_level = \
            bet_summary.promotion_bet_level
        promotion_bet_monthly.save()

        member.save()
        bet_summary.save()

        logger.info(promotion_bet_monthly)

        logger.info(bet_data)
