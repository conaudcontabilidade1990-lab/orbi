import sys

if __name__ == "__main__":
    if "--testar-ocr" in sys.argv:
        from orbi.autoteste import testar_ocr
        sys.exit(testar_ocr())
    from orbi.app import main
    main()
