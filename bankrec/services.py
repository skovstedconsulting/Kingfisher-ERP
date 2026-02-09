# bankrec/services.py
from ledger.models.journal_line import JournalLine  # tilpas path

def get_gl_bank_lines(session):
    setup = session.setup
    qs = JournalLine.objects.filter(
        journal__entity=session.entity,
        account=setup.gl_bank_account,
    )

    if session.gl_date_from:
        qs = qs.filter(journal__date__gte=session.gl_date_from)
    if session.gl_date_to:
        qs = qs.filter(journal__date__lte=session.gl_date_to)

    matched_ids = set(session.matches.values_list("gl_lines__id", flat=True))
    if matched_ids:
        qs = qs.exclude(id__in=matched_ids)

    return qs.select_related("journal", "account").order_by("journal__date", "id")


def get_unmatched_bank_lines(session):
    matched_ids = set(session.matches.values_list("bank_lines__id", flat=True))
    qs = session.staging.lines.all()
    if matched_ids:
        qs = qs.exclude(id__in=matched_ids)
    return qs.order_by("booking_date", "id")
