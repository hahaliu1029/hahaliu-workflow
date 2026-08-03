# Search module

Queries hit an inverted index rebuilt nightly; incremental updates are appended
to a delta segment merged on rebuild. Risk: deletes only mask documents in the
delta, so a failed nightly rebuild serves stale (deleted) documents all day.
