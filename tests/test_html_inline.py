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


@pytest.mark.parametrize(
    "src,expected",
    [
        # a CommonMark autolink, not an HTML tag: the autolink rule claims
        # `<scheme:...>` even though it starts like an open tag
        (
            "<https://example.com/a%20b>",
            '<a href="https://example.com/a%20b">https://example.com/a b</a>',
        ),
        # non-ASCII (IDN) autolink: punycoded href, unicode text
        (
            "<https://例子.测试/x>",
            '<a href="https://xn--fsqu00a.xn--0zwm56d/x">https://例子.测试/x</a>',
        ),
        # email autolink gains a mailto: href, but the text is unchanged
        ("<foo@bar.com>", '<a href="mailto:foo@bar.com">foo@bar.com</a>'),
        # an explicit mailto: autolink keeps the prefix in the text
        (
            "<mailto:foo@bar.com>",
            '<a href="mailto:foo@bar.com">mailto:foo@bar.com</a>',
        ),
        # a space is not allowed inside an autolink, so this is literal text
        ("<http://a.b/c d>", "&lt;http://a.b/c d&gt;"),
        # ... as is a `<` not followed by a letter, `!`, `?` or `/`
        ("<1>", "&lt;1&gt;"),
        # genuine html tags still pass through raw
        ("<a href='x'>", "<a href='x'>"),
        ("</a>", "</a>"),
        ("<div>x</div>", "<div>x</div>"),
    ],
)
def test_autolink_vs_html_inline_boundaries(src, expected):
    """Pin the boundary between CommonMark autolinks and raw inline HTML.

    Both constructs start with `<`, but `<scheme:...>`/`<email>` are autolinks
    (spec) while tags/comments/etc. are raw HTML; anything else is text.
    """
    assert MarkdownIt("commonmark").renderInline(src) == expected
