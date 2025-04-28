from janito.agent.runtime_config import runtime_config
import janito.i18n as i18n


def handle_lang(console, args=None, **kwargs):
    if not args or len(args) == 0:
        console.print(
            "[bold yellow]Uso: /lang [código_idioma] (ex: pt, en, es)[/bold yellow]"
        )
        return
    lang_code = args[0]
    runtime_config.set("lang", lang_code)
    i18n.set_locale(lang_code)
    console.print(
        f"[bold green]Idioma alterado para:[/bold green] [cyan]{lang_code}[/cyan]"
    )
