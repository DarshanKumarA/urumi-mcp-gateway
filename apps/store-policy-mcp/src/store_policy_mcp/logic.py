"""Pure lookup over the committed policy dataset."""
from .models import Input, Result
from .policies import POLICIES


def execute(query: Input) -> Result:
    return POLICIES[query.key]
