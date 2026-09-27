"""Tests for the `html_inline` rule."""

import importlib

import pytest

from markdown_it import MarkdownIt


@pytest.mark.parametrize(
    "src",
    [
        "<a>",  # open tag
        "<a/>",  # self-closing open tag
        "</a>",  # close tag
        "<!-->",  # short comment
        "<!--->",  # short comment
        "<!---->",  # shortest full comment
        "<??>",  # empty processing instruction
        "<!a>",  # declaration
        "<![CDATA[]]>",  # empty CDATA section
    ],
)
def test_shortest_constructs(src):
    """The shortest legal form of each construct is passed through as raw html."""
    assert MarkdownIt("commonmark").renderInline(src) == src


@pytest.mark.parametrize("opener", ["<![CDATA[", "<!--", "<?", "<!a", "<a", "</a"])
def test_unterminated_openers_skip_the_regex(opener, monkeypatch):
    """A run of openers that are never terminated must not run the tag regex.

    Every alternative of ``HTML_TAG_RE`` ends in a specific terminator, and its
    lazy sub-patterns rescan to the end of the input on each failed attempt,
    which made such runs quadratic.  ``html_inline`` now rejects an opener in
    constant time when the terminator it needs cannot occur, so the regex is
    never invoked here; before the fix it ran once per opener.
    """
    module = importlib.import_module("markdown_it.rules_inline.html_inline")

    real = module.HTML_TAG_RE
    calls = []

    class Counting:
        def match(self, *args, **kwargs):
            calls.append(args[1] if len(args) > 1 else None)
            return real.match(*args, **kwargs)

    monkeypatch.setattr(module, "HTML_TAG_RE", Counting())
    src = "x" + opener * 1_000  # leading "x" keeps it out of `html_block`
    html = MarkdownIt("commonmark").render(src)
    assert calls == []
    # the openers all render as escaped text
    assert html == "<p>x" + (opener.replace("<", "&lt;")) * 1_000 + "</p>\n"


def test_terminated_constructs_still_reach_the_regex(monkeypatch):
    """The quick-reject must be exactly that: a terminated construct is still
    handed to the regex and parsed as before."""
    module = importlib.import_module("markdown_it.rules_inline.html_inline")

    real = module.HTML_TAG_RE
    calls = []

    class Counting:
        def match(self, *args, **kwargs):
            calls.append(1)
            return real.match(*args, **kwargs)

    monkeypatch.setattr(module, "HTML_TAG_RE", Counting())
    src = "x <!-- c --> <?pi?> <![CDATA[d]]> <!D> <a>b</a>"
    html = MarkdownIt("commonmark").render(src)
    assert calls, "expected the regex to run for terminated constructs"
    assert html == "<p>" + src + "</p>\n"


def test_html_block_content_is_not_parsed_as_markdown():
    """A type-6 HTML block runs until a blank line, so emphasis-like and
    list-like content inside it must stay literal (CommonMark ex. 189)."""
    src = "<div>\n*not a list*\n</div>"
    assert MarkdownIt("commonmark").render(src) == src


def test_html_block_inside_list_item():
    src = "- <div>\n  *not a list*\n  </div>\n"
    assert MarkdownIt("commonmark").render(src) == (
        "<ul>\n<li>\n<div>\n*not a list*\n</div>\n</li>\n</ul>\n"
    )


def test_html_disabled_escapes_tags_but_still_parses_markdown():
    """With ``html: False`` the tags are escaped, but the text between them
    is parsed as normal markdown, so ``*not a list*`` *is* emphasised."""
    src = "<div>\n*not a list*\n</div>"
    assert MarkdownIt("default").render(src) == (
        "<p>&lt;div&gt;\n<em>not a list</em>\n&lt;/div&gt;</p>\n"
    )


def test_reported_document_matches_commonmark():
    """End-to-end pin for a user-reported document combining a code span
    inside emphasis in a list item, a ``<...>`` link destination containing
    a space, and an HTML block inside a list item."""
    src = (
        "- a **bold with `code` inside** end\n"
        "- [link](<https://example.com/a b>) and auto link https://例子.测试/x\n"
        "- <div>\n  *not a list*\n  </div>\n"
    )
    assert MarkdownIt("commonmark").render(src) == (
        "<ul>\n"
        "<li>a <strong>bold with <code>code</code> inside</strong> end</li>\n"
        '<li><a href="https://example.com/a%20b">link</a> and auto link '
        "https://例子.测试/x</li>\n"
        "<li>\n<div>\n*not a list*\n</div>\n</li>\n"
        "</ul>\n"
    )
