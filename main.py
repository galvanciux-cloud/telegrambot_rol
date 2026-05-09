#!/usr/bin/env python3
"""
main.py — Punto de entrada principal de NOVA AI Agent
Inicia el bot de Telegram y carga todos los subsistemas.
"""

import logging
import sys

from config import LOG_LEVEL, validate_config

# Configurar logging
logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("nova.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """Función principal de NOVA AI Agent."""
    print("""
    ╔══════════════════════════════════════════╗
    ║                                          ║
    ║          🤖  NOVA AI Agent  🤖           ║
    ║                                          ║
    ║    Agente de IA Conversacional           ║
    ║    HuggingFace + Telegram + RAG          ║
    ║                                          ║
    ╚══════════════════════════════════════════╝
    """)

    # Validar configuración
    errors = validate_config()
    if errors:
        print("⚠️  Errores de configuración encontrados:\n")
        for error in errors:
            print(f"  ❌ {error}")
        print("\n💡 Configura las variables en el archivo .env antes de ejecutar NOVA.")
        print("   Consulta agent.md para más información.\n")
        sys.exit(1)

    logger.info("Configuración validada correctamente")

    # Importar e inicializar el bot
    from telegram_bot import NovaTelegramBot

    bot = NovaTelegramBot()
    app = bot.build_application()

    logger.info("NOVA AI Agent iniciado. Presiona Ctrl+C para detener.")
    print("\n✅ NOVA está en línea. Esperando mensajes en Telegram...\n")
    print("   Comandos disponibles: /start, /help, /search, /wiki, etc.")
    print("   Presiona Ctrl+C para detener el bot.\n")

    # Iniciar el bot
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    try:
        from telegram import Update
        main()
    except KeyboardInterrupt:
        print("\n\n👋 NOVA se ha detenido. ¡Hasta pronto!")
        sys.exit(0)
    except ImportError as e:
        print(f"\n❌ Error de importación: {e}")
        print("💡 Asegúrate de instalar las dependencias: pip install -r requirements.txt\n")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Error fatal: {e}", exc_info=True)
        print(f"\n❌ Error fatal: {e}\n")
        sys.exit(1)
