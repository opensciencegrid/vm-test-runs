"""A helper class for generating htmls. API vaguely based on ElementTree but
the output is nicely indented for readability."""

import re
import types

def indented(string_to_indent, indent):
    """Return the indented version of a string. 'indent' is the number of spaces
    to add before each line.

    """
    indent_str = " " * indent
    string_as_list = string_to_indent.split("\n")
    result = indent_str + ("\n" + indent_str).join(string_as_list)
    return result
    

class Tag(object):
    """Holds a tag with a name, attributes and content.
    content is a list of either tags or strings.

    """
    def __init__(self, tag_name, attribs=None, **kwattribs):
        self.contents = []
        self.tag_name = tag_name
        if attribs is None:
            attribs = {}
        self.attribs = attribs
        # special case for 'class_': 'class' is used often in the htmls,
        # but is a python reserved word, so use the value of the kwarg
        # 'class_' as the value of the attribute 'class'.
        # same thing for 'type_'
        for kwattrib_name in ['class', 'type']:
            kwattrib_name_ = kwattrib_name + "_"
            if kwattribs.has_key(kwattrib_name_):
                kwattrib_value = kwattribs.pop(kwattrib_name_)
                if kwattrib_value is not None:
                    self.attribs[kwattrib_name] = kwattrib_value
        self.attribs.update(kwattribs)

    def append(self, item):
        """Add the item to the contents. Returns self for easy chaining."""
        self.contents.append(item)
        return self

    def extend(self, items):
        """Add each item to the contents. Returns self for easy chaining."""
        self.contents.extend(items)
        return self

    def append_escaped(self, text):
        """Add the value to the contents, with html special characters escaped.
        Returns self for easy chaining.

        """
        escaped = re.sub('[&]', '&amp;', text)
        escaped = re.sub('[<]', '&lt;', escaped)
        escaped = re.sub('[>]', '&gt;', escaped)
        escaped = re.sub('[%]', '&#37;', escaped)
        escaped = re.sub('\xA0', '&nbsp;', escaped)
        self.contents.append(escaped)
        return self

    def append_new_tag(self, *args, **kwargs):
        """Create a new tag and add it to the contents. Returns the new tag."""
        new_tag = Tag(*args, **kwargs)
        self.contents.append(new_tag)
        return new_tag

    def get_attribs_str(self):
        """Return the attributes as a string containing
        key1="value1" key2="value2"
        etc.
        """
        astr = ""
        attribs_list = []
        for k,v in self.attribs.iteritems():
            attribs_list.append('%s="%s"' % (k, v))
        if attribs_list:
            astr += " " + (" ".join(attribs_list))
        return astr

    def get_opening_tag(self):
        """The string for the opening tag"""
        return "<%s%s>" % (self.tag_name, self.get_attribs_str())

    def get_closing_tag(self):
        """The string for the closing tag"""
        return "</%s>" % self.tag_name

    def get_empty_tag(self):
        """The tag to use in case contents are empty"""
        return "<%s%s/>" % (self.tag_name, self.get_attribs_str())

    def set(self, attrib, newval):
        """Set an attribute. Returns self for easy chaining."""
        self.attribs[attrib] = newval
        return self

    def get(self, attrib):
        """Get an attribute."""
        return self.attribs.get(attrib)

    def __str__(self):
        if not self.contents:
            return self.get_empty_tag()
        elif len(self.contents) == 1 and not isinstance(self.contents[0], Tag):
            return self.get_opening_tag() + str(self.contents[0]) + self.get_closing_tag()
        else:
            return "%s\n%s\n%s" % (self.get_opening_tag(), "\n".join((indented(str(x), 2) for x in self.contents)), self.get_closing_tag())
        
def SubTag(parent, *args, **kwargs):
    """Factory function. A convenient alias for Tag.append_new_tag -- compare
    to ElementTree.SubElement()"""
    return parent.append_new_tag(*args, **kwargs)


class Html(object):
    def __init__(self, page_title=None, css_inline=None, css_link=None):
        self.page_title = page_title
        self.css_inline = css_inline
        self.css_link = css_link

        self.html = Tag("html", lang="en")
        self.head = SubTag(self.html, "head")
        self.head.append_new_tag("meta", charset="utf-8")
        if self.page_title:
            self.head.append_new_tag("title").append(self.page_title)
        if self.css_link:
            self.head.append_new_tag("link", rel="stylesheet", type_="text/css", href=self.css_link)
        if self.css_inline:
            self.head.append_new_tag("style", type_='text/css').append(self.css_inline)
        self.body = SubTag(self.html, "body")

    def __str__(self):
        return "<!DOCTYPE html>\n" + str(self.html)


