from markdown_it import MarkdownIt


def _make_linkify_md():
    return MarkdownIt(options_update={"linkify": True}).enable("linkify")


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


# CommonMark autolinks (``<scheme:...>``) and the linkify extension are
# different mechanisms: the former is core CommonMark and always on, the
# latter is an optional core rule driven by the ``linkify`` option.
# The tests below pin the boundary on both sides.


def test_spec_autolink_works_without_linkify():
    assert MarkdownIt("commonmark").render("<https://example.com>") == (
        '<p><a href="https://example.com">https://example.com</a></p>\n'
    )


def test_linkify_does_not_rewrap_spec_autolink():
    assert _make_linkify_md().render("<https://example.com>") == (
        '<p><a href="https://example.com">https://example.com</a></p>\n'
    )


def test_bare_url_not_linked_without_linkify():
    assert MarkdownIt("commonmark").render("https://example.com") == (
        "<p>https://example.com</p>\n"
    )


def test_bare_url_linkified_when_enabled():
    assert _make_linkify_md().render("https://example.com") == (
        '<p><a href="https://example.com">https://example.com</a></p>\n'
    )


def test_bare_idn_url_linkified_with_punycode_href():
    assert _make_linkify_md().render("https://例子.测试/x") == (
        '<p><a href="https://xn--fsqu00a.xn--0zwm56d/x">https://例子.测试/x</a></p>\n'
    )


def test_fuzzy_domain_gets_default_scheme():
    assert _make_linkify_md().render("www.example.com") == (
        '<p><a href="http://www.example.com">www.example.com</a></p>\n'
    )


def test_link_destination_with_space_in_pointy_brackets():
    """A ``<...>`` destination may contain spaces (percent-encoded in the
    output); linkify must not treat the destination as plain text."""
    assert _make_linkify_md().render("[link](<https://example.com/a b>)") == (
        '<p><a href="https://example.com/a%20b">link</a></p>\n'
    )


def test_linkify_skips_markdown_links_and_code_spans():
    md = _make_linkify_md()
    assert md.render("[a](https://x.com) `https://y.com` https://z.com") == (
        '<p><a href="https://x.com">a</a> <code>https://y.com</code> '
        '<a href="https://z.com">https://z.com</a></p>\n'
    )


def test_linkify_skips_escaped_scheme():
    assert _make_linkify_md().render(r"http\://example.com/") == (
        "<p>http://example.com/</p>\n"
    )


def test_linkify_skips_html_block_content():
    src = "<div>\nhttps://example.com\n</div>"
    assert _make_linkify_md().render(src) == src
