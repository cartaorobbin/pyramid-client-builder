"""Trivial pycornmarsh-compatible view predicates for testing.

These replicate the pycornmarsh predicate pattern: always-true predicates
that serve purely as metadata carriers on Pyramid view introspectables.
No runtime dependency on pycornmarsh is needed.
"""


class _AlwaysTruePredicate:
    """Base for metadata-only view predicates."""

    PRED_ID = ""

    def __init__(self, val, _):
        self.val = val

    def text(self):
        return f"{self.PRED_ID} = {self.val}"

    phash = text

    def __call__(self, context, request):
        return True


class PCMRequestPredicate(_AlwaysTruePredicate):
    PRED_ID = "pcm_request"


class PCMResponsesPredicate(_AlwaysTruePredicate):
    PRED_ID = "pcm_responses"


class PCMShowPredicate(_AlwaysTruePredicate):
    PRED_ID = "pcm_show"


def includeme(config):
    """Register pycornmarsh-compatible view predicates."""
    config.add_view_predicate("pcm_request", PCMRequestPredicate)
    config.add_view_predicate("pcm_responses", PCMResponsesPredicate)
    config.add_view_predicate("pcm_show", PCMShowPredicate)
