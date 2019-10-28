import logging

from calendar import monthrange
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from django.utils import timezone

from account.models import Member
from grizzly.celery import app
from promotion.models import (GAME_TYPE_ELECTRONICS,
                              PromotionBet,
                              PromotionBetLevel,
                              PromotionBetMonthly,
                              ImportExportLog,
                              REQUEST_LOG_COMPLETED,
                              REQUEST_LOG_CANCELED,
                              REQUEST_LOG_DELETED,
                              Summary)

logger = logging.getLogger(__name__)


@app.task(name='promotion_bet_import')
def promotion_bet_import(import_data, user_id, game_type, request_log_id):
    user = User.objects.get(id=user_id)
    request_log = ImportExportLog.objects.get(id=request_log_id)
    today = timezone.localtime(timezone.now())
    week_begin = (today - timedelta(days=today.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    week_end = week_begin + timedelta(days=6)
    cycle_year = week_begin.year
    cycle_month = week_begin.month

    member_bet_summary = Summary.objects \
        .filter(game_type=game_type,
                updated_at__lt=week_begin,
                promotion_bet_level__isnull=False) \
        .order_by('-updated_at')
    update_members_summary(member_bet_summary, today)

    deposits = []
    for data in reversed(import_data):
        logger.info(data)
        try:
            username = data.get('username')
            amount = float(data.get('amount'))
            if amount < 0.0:
                update_request_log(request_log,
                                   REQUEST_LOG_CANCELED,
                                   f'Negative amount found in imported data: '
                                   f'{username} ({amount:,.2f})')
                return None

            member, created = Member.objects.get_or_create(
                username=username)

            if created:
                member.created_by = user
            else:
                member.updated_by = user

            deposits.append(
                PromotionBet(
                    member=member,
                    username=username,
                    amount=amount,
                    cycle_begin=week_begin,
                    cycle_end=week_end,
                    game_type=game_type,
                    request_log=request_log,
                    created_by=user,
                )
            )
        except Exception as exc:
            logger.error(f'Error: {exc} -- {data.get("username")}')
            update_request_log(request_log,
                               REQUEST_LOG_CANCELED,
                               f'Error: {exc}')
            return None

    try:
        bet_deposits = PromotionBet.objects.bulk_create(deposits)
        logger.info(f'{len(bet_deposits)} promotion bet deposits created.')
    except Exception as exc:
        logger.error(exc)
        update_request_log(request_log,
                           REQUEST_LOG_CANCELED,
                           f'Error: {exc}')
        return None

    for bet in bet_deposits:
        member = bet.member
        game_type = bet.game_type
        amount = bet.amount
        logger.info(f'Processing: {member} -- {amount:,.2f}')
        bet_summary, created = Summary.objects.get_or_create(
            member=member, game_type=game_type)

        if created:
            bet_summary.created_by = user
        else:
            bet_summary.updated_by = user

        bet_summary.total_promotion_bet += amount

        previous_bets = PromotionBet.objects \
            .filter(game_type=game_type,
                    member=member,
                    cycle_begin__lt=week_begin,
                    active=True) \
            .order_by('cycle_begin')
        previous_total_bet_amount = previous_bets.aggregate(
            Sum('amount')).get('amount__sum') or 0.0

        if previous_bets.exists() and new_cycle(previous_bets, week_begin):
            if bet_summary.promotion_bet_level:
                bet_summary.total_bonus += \
                    bet_summary.promotion_bet_level.weekly_bonus

                if first_week(previous_bets.last().cycle_begin):
                    bet_summary.total_bonus += \
                        bet_summary.promotion_bet_level.monthly_bonus

        bet_levels = PromotionBetLevel.objects.filter(
            game_type=game_type,
            total_bet__lte=bet_summary.total_promotion_bet)
        current_level = bet_levels.last()

        bet_summary.promotion_bet_level = current_level
        bet.promotion_bet_level = current_level

        bet_summary.current_week_bonus = \
            bet_levels.exclude(total_bet__lte=previous_total_bet_amount) \
                      .aggregate(Sum('bonus')).get('bonus__sum') or 0.0

        promotion_bet_monthly, created = PromotionBetMonthly.objects.\
            get_or_create(member=member, cycle_year=cycle_year,
                          cycle_month=cycle_month, game_type=game_type)
        if created:
            promotion_bet_monthly.cycle_year = cycle_year
            promotion_bet_monthly.cycle_month = cycle_month
            promotion_bet_monthly.cycle_begin = week_begin

        promotion_bet_monthly.total_bet += amount
        promotion_bet_monthly.promotion_bet_level = current_level
        promotion_bet_monthly.cycle_end = week_end

        promotion_bet_monthly.save()
        bet_summary.save()
        bet.save()

    logger.info('Import complete.')
    update_request_log(request_log, REQUEST_LOG_COMPLETED)


def update_members_summary(member_bet_summary, today):
    for summary in member_bet_summary:
        summary.total_bonus += summary.current_week_bonus
        summary.current_week_bonus = 0

        summary.previous_week_bet_level = summary.promotion_bet_level

        if summary.updated_at.month == \
                (today - timedelta(days=today.day)).month:
            summary.previous_month_bet_level = summary.promotion_bet_level

        summary.save(update_fields=['current_week_bonus',
                                    'previous_week_bet_level',
                                    'previous_month_bet_level',
                                    'total_bonus',
                                    'updated_at'])


def new_cycle(previous_bets, week_begin):
    return previous_bets.last().cycle_begin < week_begin


@app.task(name='compute_total_bonus')
def compute_total_bonus():
    today = timezone.localtime(timezone.now())
    members = Summary.objects.filter(promotion_bet_level__isnull=False) \
                             .distinct('member') \
                             .order_by('member')

    logger.info(f'Member count: {members.count()}')

    for i, member in enumerate(members):
        logger.info(f'({i + 1}) {member.member.username}')

        bets = PromotionBet.objects.filter(member=member.member) \
                                   .order_by('game_type',
                                             'created_at')

        if not bets.exists():
            continue

        total_bets = 0
        month_bonus = 0
        old_cycle = None
        old_bet_level = None
        bet_summary = {}
        for bet in bets:
            game_type = bet.game_type
            bet_summary.setdefault(game_type, {})
            cycle_begin = timezone.localtime(bet.cycle_begin).date()
            cycle_end = timezone.localtime(bet.cycle_end).date()

            if cycle_begin <= today.date() <= cycle_end:
                continue

            total_bets += bet.amount

            cycle_month = f'{cycle_begin:%Y%m}'
            bet_summary[game_type].setdefault(
                cycle_month, {
                    'cycle_year': cycle_begin.year,
                    'cycle_month': cycle_begin.month,
                    'cycle_begin': cycle_begin,
                    'total_weekly_bonus': 0})
            bet_summary[game_type][cycle_month]['cycle_end'] = cycle_end

            bet_levels = PromotionBetLevel.objects \
                .filter(game_type=game_type, total_bet__lte=total_bets) \
                .order_by('total_bet')

            if bet_levels.exists():
                month_summary = bet_summary[game_type][cycle_month]

                bet_level = bet_levels.last()
                if first_week(cycle_begin):
                    month_bonus = bet_level.monthly_bonus
                    month_summary['month_bonus'] = month_bonus

                if old_bet_level and old_cycle == cycle_begin:
                    month_summary['total_weekly_bonus'] -= \
                        old_bet_level.weekly_bonus
                month_summary['total_weekly_bonus'] += bet_level.weekly_bonus

                old_bet_level = bet_level

            old_cycle = cycle_begin

        last_total_bets = 0
        for game_type, summary in bet_summary.items():
            total_bonus = 0
            accumulated_bonus = 0
            for key, month_summary in summary.items():
                cycle_year = month_summary.get('cycle_year')
                cycle_month = month_summary.get('cycle_month')
                month_bets = bets.filter(game_type=game_type,
                                         cycle_begin__year=cycle_year,
                                         cycle_begin__month=cycle_month)

                bet_amount_current_cycle = 0
                bets_current_cycle = month_bets.filter(
                    Q(cycle_begin__lte=today) & Q(cycle_end__gte=today))
                if bets_current_cycle.exists():
                    bet_amount_current_cycle = \
                        bets_current_cycle.aggregate(Sum('amount')) \
                                          .get('amount__sum') or 0

                month_bets = month_bets.aggregate(Sum('amount')) \
                                       .get('amount__sum') or 0

                total_bets = last_total_bets + month_bets - \
                    bet_amount_current_cycle
                bet_levels = PromotionBetLevel.objects \
                    .filter(game_type=game_type,
                            total_bet__gte=last_total_bets,
                            total_bet__lte=total_bets)
                accumulated_bonus = bet_levels.aggregate(Sum('bonus')) \
                                              .get('bonus__sum') or 0
                last_total_bets += month_bets

                try:
                    monthly_bet, created = PromotionBetMonthly.objects \
                        .get_or_create(member=member.member,
                                       game_type=game_type,
                                       cycle_year=cycle_year,
                                       cycle_month=cycle_month)
                    monthly_bet.total_bet = month_bets
                    monthly_bet.accumulated_bonus = accumulated_bonus
                    monthly_bet.total_weekly_bonus = \
                        month_summary.get('total_weekly_bonus', 0)
                    monthly_bet.month_bonus = \
                        month_summary.get('month_bonus', 0)
                    monthly_bet.cycle_begin = make_tz_aware(
                        month_summary.get('cycle_begin'))
                    monthly_bet.cycle_end = make_tz_aware(
                        month_summary.get('cycle_end'))

                    if created and bet_levels.exists():
                        bet_level = bet_levels.last()
                        monthly_bet.promotion_bet_level = bet_level

                    monthly_bet.save(update_fields=['total_bet',
                                                    'promotion_bet_level',
                                                    'accumulated_bonus',
                                                    'total_weekly_bonus',
                                                    'month_bonus',
                                                    'cycle_begin',
                                                    'cycle_end'])
                except Exception as exc:
                    logger.error(exc)
                    logger.info(month_summary)

                total_bonus += accumulated_bonus + \
                    month_summary.get('total_weekly_bonus', 0) + \
                    month_summary.get('month_bonus', 0)

            try:
                member_summary, created = Summary.objects.get_or_create(
                    member=member.member, game_type=game_type)
                member_summary.total_bonus = total_bonus

                member_summary.save()
            except Exception as exc:
                logger.error(exc)
                logger.info(f'Member summary for {member} {game_type}')

    logger.info(f'Compute total bonus completed.')


def first_week(cycle_begin):
    return cycle_begin.day <= 7


def make_tz_aware(unaware_tz_cycle):
    return timezone.make_aware(
        datetime.strptime(
            f'{unaware_tz_cycle:%Y-%m-%d}', '%Y-%m-%d'))


@app.task(name='migrate_member_summary')
def migrate_member_summary():
    members = Member.objects.all()
    for member in members:
        logger.info(f'Migrating member summary {member.username}')
        summary, created = Summary.objects.get_or_create(
            member=member, game_type=GAME_TYPE_ELECTRONICS)

        if created:
            summary.promotion_bet_level = member.promotion_bet_level
            summary.previous_week_bet_level = member.previous_week_bet_level
            summary.previous_month_bet_level = member.previous_month_bet_level
            summary.total_promotion_bet = member.total_promotion_bet
            summary.total_promotion_bonus = member.total_promotion_bonus
            summary.current_week_bonus = member.current_week_bonus

        summary.save()
    logger.info(f'Migrating member summary completed.')


@app.task(name='promotion_cancel_request')
def cancel_request(request_log_id):
    STATUS_ONGOING = 0
    request_log = ImportExportLog.objects.get(id=request_log_id)
    if request_log.status == STATUS_ONGOING:
        request_log.status = 2
        request_log.memo = f'Request canceled'
        request_log.save(update_fields=['status', 'memo', 'updated_at'])


def update_member_bet_details(bet, user=None):
    member = bet.member
    game_type = bet.game_type
    logger.info(f'Updating details for member: {member.username} {game_type}')
    logger.info(f'Removing bet: {bet.amount:,.2f} ({bet.id})')
    today = timezone.localtime(timezone.now())
    week_begin = (today - timedelta(days=today.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    week_end = week_begin + timedelta(days=6)

    cycle_begin = timezone.localtime(bet.cycle_begin)
    member_summary = Summary.objects.get(member=member,
                                         game_type=game_type)
    member_summary.total_promotion_bet -= bet.amount
    member_summary.updated_by = user

    bet_levels = PromotionBetLevel.objects \
        .filter(game_type=game_type,
                total_bet__lte=member_summary.total_promotion_bet) \
        .order_by('total_bet')

    member_summary.promotion_bet_level = bet_levels.last()

    member_previous_bets = PromotionBet.objects \
        .filter(game_type=game_type, member=member,
                cycle_begin__lt=cycle_begin,
                active=True)
    previous_total = member_previous_bets.aggregate(
        Sum('amount')).get('amount__sum') or 0

    member_month_bet = PromotionBetMonthly.objects \
        .get(game_type=game_type, member=member,
             cycle_year=cycle_begin.year,
             cycle_month=cycle_begin.month)
    member_month_bet.total_bet -= bet.amount

    if week_begin == cycle_begin:
        member_summary.current_week_bonus = bet_levels \
            .filter(total_bet__gt=previous_total,
                    total_bet__lte=member_summary.total_promotion_bet) \
            .aggregate(Sum('bonus')) \
            .get('bonus__sum') or 0

        if first_week(cycle_begin):
            member_month_bet.month_bonus = 0
    else:
        bet_levels = PromotionBetLevel.objects \
            .filter(game_type=game_type,
                    total_bet__lte=previous_total + bet.amount) \
            .order_by('total_bet')

        if bet_levels.exists():
            accumulated_levels = bet_levels.filter(
                total_bet__gt=previous_total,
                total_bet__lte=previous_total + bet.amount)
            accumulated_bonus = accumulated_levels.aggregate(
                Sum('bonus')).get('bonus__sum') or 0

            member_month_bet.accumulated_bonus -= accumulated_bonus
            member_month_bet.total_weekly_bonus -= \
                bet_levels.last().weekly_bonus

            if member_summary.total_bonus <= accumulated_bonus + \
                    bet_levels.last().weekly_bonus:
                member_summary.total_bonus = 0
            else:
                member_summary.total_bonus -= accumulated_bonus + \
                    bet_levels.last().weekly_bonus

            if first_week(cycle_begin):
                if member_summary.total_bonus >= \
                        bet_levels.last().monthly_bonus:
                    member_summary.total_bonus -= \
                        bet_levels.last().monthly_bonus

                if member_month_bet.month_bonus >= \
                        bet_levels.last().monthly_bonus:
                    member_month_bet.month_bonus -= \
                        bet_levels.last().monthly_bonus

    member_month_bet.save()
    member_summary.save()


@app.task(name='delete_request')
def delete_request(request_log_id, user_id):
    user = User.objects.get(id=user_id)

    request_log = ImportExportLog.objects.get(id=request_log_id)
    bets = PromotionBet.objects.filter(request_log=request_log, active=True)

    for bet in bets:
        update_member_bet_details(bet, user)

    bets.update(active=False)


@app.task(name='revert_bets')
def revert_bets(bet_ids, user_id):
    user = User.objects.get(id=user_id)
    member_bets = PromotionBet.objects.filter(id__in=bet_ids)
    for bet in member_bets:
        update_member_bet_details(bet, user)


def update_request_log(request_log, status, memo=None):
    request_log.status = status
    request_log.memo = memo
    request_log.save(
        update_fields=['status', 'memo', 'updated_at'])
