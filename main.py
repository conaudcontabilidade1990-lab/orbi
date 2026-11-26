import sys

if __name__ == "__main__":
    if "--testar-ocr" in sys.argv:
        from orbi.autoteste import testar_ocr
        sys.exit(testar_ocr())
    import ctypes
    try:  # identidade própria na barra de tarefas (ícone do Orbi, não o do Python)
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Conaud.Orbi")
    except Exception:
        pass
    if getattr(sys, "frozen", False) and sys.stderr is None:  # .exe sem console: guarda erros
        from orbi import config as _c
        _c.PASTA_LOGS.mkdir(parents=True, exist_ok=True)
        sys.stderr = open(_c.PASTA_LOGS / "erros.log", "a", encoding="utf-8", buffering=1)
    from orbi import atualizacao
    try:
        if atualizacao.instalar_se_no_servidor():   # aberto do servidor (Z:\\Orbi): instala aqui e reabre
            sys.exit(0)
    except Exception as e:
        print(f"instalação local falhou: {e}", file=sys.stderr)
    from orbi.app import main
    main()
