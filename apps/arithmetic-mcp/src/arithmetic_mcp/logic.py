"""Pure decimal arithmetic; explicit local precision and rounding policy."""
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from .models import Input, Result


def normalized(value: Decimal) -> str:
    if not value:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def execute(query: Input) -> Result:
    # 100 inputs of at most 18 integer + 6 fractional digits need <=26
    # significant digits for an exact sum. Context is local, never global.
    with localcontext() as context:
        context.prec = 40
        context.rounding = ROUND_HALF_EVEN
        values = [Decimal(value) for value in query.amounts]
        total = sum(values, Decimal(0))
        average = (total / Decimal(len(values))).quantize(Decimal("0.000001"))
        return Result(count=len(values), total=normalized(total), average=normalized(average),
            minimum=normalized(min(values)), maximum=normalized(max(values)), currency=query.currency)
