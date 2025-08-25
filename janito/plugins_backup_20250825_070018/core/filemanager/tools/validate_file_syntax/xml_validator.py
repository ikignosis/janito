from janito.i18n import tr


def validate_xml(path: str) -> str:
    try:
        from lxml import etree
    except ImportError:
        return tr("⚠️ lxml not installed. Cannot validate XML.")
    with open(path, "rb") as f:
        etree.parse(f)
    return "✅ OK"
