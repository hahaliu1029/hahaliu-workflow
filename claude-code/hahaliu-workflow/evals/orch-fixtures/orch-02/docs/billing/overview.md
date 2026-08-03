# Billing module

Invoices are generated monthly with mid-cycle proration computed per day.
Payment retries follow a 1/3/7-day backoff. Risk: proration rounds per line item,
so multi-line invoices can drift by a few cents from the advertised total.
