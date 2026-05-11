from django.utils import timezone


def generate_pseudocode(partner_code: str = None) -> str:
    """Generate unique participant pseudocode: PSN-YYYY-NNNNNN."""
    from .models import Participant
    year = timezone.now().year
    prefix = f"PSN-{year}-"
    last = Participant.objects.filter(pseudo_code__startswith=prefix).order_by('-pseudo_code').first()
    if last:
        try:
            last_num = int(last.pseudo_code.split('-')[-1])
        except ValueError:
            last_num = 0
        next_num = last_num + 1
    else:
        next_num = 1
    return f"{prefix}{next_num:06d}"
