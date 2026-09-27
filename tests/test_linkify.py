import pytest

from markdown_it import MarkdownIt


def test_token_levels():
    mdit = MarkdownIt(options_update={"linkify": True}).enable("linkify")
    tokens = mdit.parse("www.python.org")
    inline = tokens[1]
    assert inline.type == "inline"
    assert inline.children
    link_open = inline.children[0]
    assert link_open.type == "link_open"
    link_text = inline.children[1]
    assert link_text.type == "text"
    link_close = inline.children[2]
    assert link_close.type == "link_close"

    # Assert that linkify tokens have correct nesting levels
    assert link_open.level == 0
    assert link_text.level == 1
    assert link_close.level == 0


def _make_linkify_md():
    return MarkdownIt(options_update={"linkify": True}).enable("linkify")


def test_mailto_link_text_decodes_punycode_host():
    """A bare email matched by linkify is normalised with a `mailto:` prefix,
    so a punycode host is decoded for display while the href keeps the ASCII
    form (mirrors tests/test_port/fixtures/punycode.md)."""
    assert _make_linkify_md().render("test xn--n3h@xn--n3h.net foo") == (
        '<p>test <a href="mailto:xn--n3h@xn--n3h.net">xn--n3h@☃.net</a>'
        " foo</p>\n"
    )


def test_mailto_prefixed_link_text_keeps_prefix():
    """Text that already includes `mailto:` keeps it in the link text."""
    assert _make_linkify_md().render("mailto:xn--n3h@xn--n3h.net") == (
        '<p><a href="mailto:xn--n3h@xn--n3h.net">mailto:xn--n3h@☃.net</a></p>\n'
    )


@pytest.mark.parametrize(
    "src,expected",
    [
        # bare URLs and emails are linked by the linkify extension ...
        (
            "see https://example.com/a b",
            '<p>see <a href="https://example.com/a">https://example.com/a</a> b</p>\n',
        ),
        (
            "mail foo@bar.com now",
            '<p>mail <a href="mailto:foo@bar.com">foo@bar.com</a> now</p>\n',
        ),
        # ... including IDN hosts: punycoded href, unicode text
        (
            "go https://例子.测试/x now",
            '<p>go <a href="https://xn--fsqu00a.xn--0zwm56d/x">'
            "https://例子.测试/x</a> now</p>\n",
        ),
    ],
)
def test_linkify_extension_links_bare_text(src, expected):
    assert _make_linkify_md().render(src) == expected


@pytest.mark.parametrize(
    "src",
    [
        # CommonMark autolinks are the autolink rule's job, not linkify's:
        # the extension must leave them byte-identical
        "<https://例子.测试/x>",
        "<foo@bar.com>",
        "<mailto:foo@bar.com>",
        # code spans are never linkified
        "`https://example.com`",
        # link text of markdown links is not re-linkified
        "[https://example.com](https://example.com)",
        # content of raw html <a> tags is not re-linkified
        '<a href="https://example.com">https://example.com</a>',
        # a pointy-bracket link destination may contain spaces and is a
        # markdown link, not something linkify should touch
        "[link](<https://example.com/a b>)",
    ],
)
def test_linkify_extension_leaves_other_constructs_alone(src):
    """The linkify extension must not change constructs it does not own."""
    assert _make_linkify_md().render(src) == MarkdownIt("commonmark").render(src)


def test_spec_autolink_does_not_need_the_extension():
    """`<...>` autolinks are CommonMark, independent of the linkify extension."""
    md = MarkdownIt("commonmark")
    assert (
        md.render("<https://例子.测试/x>")
        == '<p><a href="https://xn--fsqu00a.xn--0zwm56d/x">'
        "https://例子.测试/x</a></p>\n"
    )
    # ... while bare URLs stay plain text without the extension
    assert md.render("https://例子.测试/x") == "<p>https://例子.测试/x</p>\n"
