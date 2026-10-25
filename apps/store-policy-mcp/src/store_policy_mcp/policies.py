"""Version-controlled operational demo guidance; no file or network lookup."""
from types import MappingProxyType
from .models import Result

POLICIES = MappingProxyType({
    "cod": Result(key="cod", title="Cash on Delivery",
        guidance="Collect payment on delivery. A COD order is not prepaid; its order status alone does not prove payment was collected."),
    "dispatch": Result(key="dispatch", title="Dispatch checks",
        guidance="Review processing orders for fulfillment readiness. Keep on-hold orders out of dispatch until the reason for the hold has been reviewed and an operator releases them. This reference does not change order status."),
    "cancellation": Result(key="cancellation", title="Cancellation review",
        guidance="Before cancelling, review fulfillment and payment state with an operator. Changing an order status is not a refund operation. This demo reference does not authorize or perform a cancellation or refund."),
})
