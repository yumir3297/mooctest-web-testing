"""Qualification positive sample: one pass, one real product defect.

``_submit`` models the application: it keeps a whitespace-only title, which is
the defect reported in the manifest.
"""


def _submit(text):
    # product behaviour: only the empty string is rejected, whitespace is kept
    return [] if text == "" else [text]


def test_add_valid():
    assert _submit("Buy milk") == ["Buy milk"]


def test_reject_blank_title():
    assert _submit("   ") == []
