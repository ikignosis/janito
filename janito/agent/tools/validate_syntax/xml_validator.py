from janito.i18n import tr


def validate_xml(file_path: str) -> str:
    try:
        from lxml import etree
    except ImportError:
        return tr("⚠️ lxml not installed. Cannot validate XML.")
    with open(file_path, "rb") as f:
        etree.parse(f)
    return "✅ Syntax valid"
