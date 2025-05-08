import logging
from utils.telegram import notificar_grupo
from core.settings import APP_NAME
class TelegramLogHandler(logging.Handler):
    """
    Handler de log personalizado que envia mensagens de erro para o Telegram.
    """
    def __init__(self, level=logging.ERROR):
        super().__init__(level)
        
    def emit(self, record):
        if record.levelno >= self.level:
            try:
                mensagem = self.format(record)
                notificar_grupo(f"⚠️ ERRO no {APP_NAME}:\n\n{mensagem}")
            except Exception:
                self.handleError(record) 