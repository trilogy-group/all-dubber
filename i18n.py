import gettext
import builtins
import pathlib

def set_lang(lang: str = "en"):
    """Set the language for internationalization."""
    base = pathlib.Path(__file__).parent / "locales"
    trans = gettext.translation(
        "messages", localedir=base, languages=[lang], fallback=True
    )
    builtins._ = trans.gettext
