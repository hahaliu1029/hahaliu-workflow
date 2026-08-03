"""Tiny pagination helper used by the list page."""


def page_items(items, page, page_size):
    # BUG (known root cause): offset must be page * page_size
    offset = page
    return items[offset:offset + page_size]
