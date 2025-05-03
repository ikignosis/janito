import importlib
import threading
import hashlib

_current_locale = "en"
_translations = {}
_lock = threading.Lock()


def set_locale(locale):
    global _current_locale, _translations
    with _lock:
        _current_locale = locale
        if locale == "en":
            _translations = {}
        else:
            try:
                mod = importlib.import_module(f"janito.i18n.{locale}")
                _translations = getattr(mod, "translations", {})
            except ImportError:
                _translations = {}


def tr(msg, **kwargs):
    """Translate message to current locale, usando hash SHA-1 da mensagem como chave."""
    msg_hash = hashlib.sha1(msg.encode("utf-8", errors="surrogatepass")).hexdigest()
    template = _translations.get(msg_hash, msg)
    try:
        return template.format(**kwargs)
    except Exception:
        return template  # fallback if formatting fails


# Inicializa com o idioma padrão (en)
set_locale("en")
